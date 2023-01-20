from app.services import DomainServices, logger, pprint, db, ModelStatus, config
from app.models import Attachment, Lesson, LessonAttachment
from werkzeug.utils import secure_filename
from typing import List
import os
import subprocess
import threading
from datetime import datetime


class AttachmentServices(DomainServices):
    def __init__(self, request, *args, **kwargs):
        super().__init__(request, *args, **kwargs)


    def allowed_file(self, filename):
	    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


    def save(self, *args, **kwargs):
        
        file = self._flask_request.files['file']

        logger.info("Persistindo arquivo: {}".format(file.filename))

        if not self.allowed_file(file.filename):
            self.raise_error("Verifique a extensão do arquivo '{}'. Extensões permitidas: '{}'".format(file.filename, config.ALLOWED_EXTENSIONS))

        filename = secure_filename(file.filename)

        files_with_same_name = Attachment.query.filter_by(name=filename).all()

        if len(files_with_same_name):
            extension = filename.split('.')[-1] # Pegando a extensão do arquivo
            real_file_name = filename.split('.')[:-1] # Pegando todo o nome até a extensão

            #print(extension, real_file_name)
            logger.debug("Quantidade de arquivos com o mesmo nome: {}".format(len(files_with_same_name)))
            filename = '{}_{}.{}'.format(''.join(real_file_name), len(files_with_same_name) + 1, extension)
            
            #self.raise_error("Já existe arquivo com esse nome.")
        
        file_path = os.path.join(config.UPLOAD_FOLDER, filename)
      
        file.save(file_path)
        size = os.stat(file_path).st_size

        file_format = filename.rsplit(".", 1)[1]

        logger.info("Fazendo upload: {} - {} - {}".format(filename, file_path, file_format))

        new_attachement = Attachment.create(name=filename, cdn_link=file_path, format=file_format, size=size)
        
        self.close_session()
        self._process_result = new_attachement.id


    def tmp_save(self, *args, **kwargs):
        file = self._flask_request.files['file']

        logger.info("Persistindo arquivo: {}".format(file.filename))

        if not self.allowed_file(file.filename):
            self.raise_error("Verifique a extensão do arquivo '{}'. Extensões permitidas: '{}'".format(file.filename, config.ALLOWED_EXTENSIONS))

        filename = secure_filename(file.filename)

        file_path = os.path.join(config.UPLOAD_TMP_FOLDER, filename)
      
        file.save(file_path)
       
        self.close_session()
        self._process_result = filename


    def tmp_consolide(self, transaction_id:str, *args, **kwargs):
        file_paths = []

        for file in os.listdir(config.UPLOAD_TMP_FOLDER):
            if transaction_id in file:
                file_paths.append(os.path.join(config.UPLOAD_TMP_FOLDER, file))

        # Ordenando os arquivos
        file_paths.sort(key=lambda element: int(element.split('.')[0].split('__')[1]))

        logger.debug("Arquivos temporários: {}".format(file_paths))

        attachment_name = '{}.{}'.format(transaction_id, file.split('.')[-1])
        output_file = os.path.join(config.UPLOAD_TMP_FOLDER, attachment_name)
        
        logger.debug("Anexo que será gerado: {}".format(attachment_name))
        
        threading.Thread(target=self.make_concat_async_file_writer, args=(file_paths, output_file)).start()
        
        self.close_session()
        self._process_result = transaction_id


    def close_transactions(self, *args, **kwargs):
        """
        Função para fazer o merge dos vídeos com o ffmpeg

        Exemplo do que esperar no body da requisição: {'lessonId': this._lesson.id, 'transactions': transactions}
        """
        
        lesson_id = self._body_params['lessonId']
        transactions = self._body_params['transactions']

        logger.debug("Transações '{}' a serem consolidadas para a aula: {}".format(transactions, lesson_id))

        file_paths = []

        # Varrendo o diretório de arquivos que foram feitos o upload:
        for file in os.listdir(config.UPLOAD_TMP_FOLDER):
            if file.split('.')[0] in transactions:
                file_paths.append(os.path.join(config.UPLOAD_TMP_FOLDER, file))

        # Ordenando os arquivos pela data de modificação
        file_paths.sort(key=lambda element: os.path.getmtime(element))

        logger.debug("Arquivos temporários: {}".format(file_paths))

        # Carregando a aula
        lesson = Lesson.query.filter_by(id=lesson_id).first()

        attachment_name = '{}-{}-ao-vivo.{}'.format(lesson.name.replace(' ', '_'), datetime.now().strftime('%d_%m_%y_%H_%M'), file.split('.')[-1])
        output_file = os.path.join(config.UPLOAD_FOLDER, attachment_name)
        
        logger.debug("Anexo que será gerado: {}".format(output_file))

        # Criando o novo anexo:
        new_attachment = Attachment.create(
            name=attachment_name, 
            cdn_link=output_file, 
            format=file.split('.')[-1], 
            size=-1, 
            status=ModelStatus.PROCESSING.value)

        # Associando a aula com o novo anexo gerado:
        new_lesson_attachment = LessonAttachment.create(lesson_id=lesson.id, attachment_id=new_attachment.id, main_attachment=True)

        command = self.generate_ffmpeg_command(file_paths, output_file)
        
        threading.Thread(target=self.make_video_concat_async, args=(command, file_paths, new_attachment.id, output_file)).start()
        
        self.close_session()
        self._process_result = new_attachment.id

        
    def download(self, id, *args, **kwargs):
        from flask import send_file

        attachment = Attachment.query.filter(Attachment.id == id, Attachment.status!=ModelStatus.DELETED.value).first()
        
        if not attachment: 
            self.raise_error("Verifique a validade do anexo requisitado. Ele não encontra-se disponível.")
        
        logger.debug("Anexo requerido: {} - {}".format(attachment.name, attachment.status))

        if attachment.status == ModelStatus.PROCESSING.value:   
            self.raise_error("O anexo/material ainda está em processamento. Aguarde, por favor.")
        
        self.clean_session()
        
        try:
            return send_file(attachment.cdn_link, attachment.name)
        except Exception as not_found_file:
            logger.exception(not_found_file)
            self.raise_error("O Arquivo não está mais disponível para Download.")
        

    def treat_many(self, *args, **kwargs):
               
        files = self._flask_request.files

        file_paths, streams, resized_paths = [], [], []

        # Salvando arquivos no ambiente temporário:
        for file in files.values():
            logger.info("Persistindo arquivo: {}".format(file.filename))

            if not self.allowed_file(file.filename):
                self.raise_error("Verifique a extensão do arquivo. Extensões permitidas: '{}'".format(config.ALLOWED_EXTENSIONS))

            filename = secure_filename(file.filename)
                    
            file_path = os.path.join(config.UPLOAD_TMP_FOLDER, filename)
        
            file.save(file_path)
            
            file_paths.append(file_path) 
        
        logger.debug("Arquivos temporários: {}".format(file_paths))
        
        """
        Devemos montar uma string de chamada parecida com:
        ffmpeg -i /home/pyduh/Enterprise-Projects/aula-plus.back/tmp-files/1-Aula_3-2020-06-29T051449.762Z.webm 
        -i /home/pyduh/Enterprise-Projects/aula-plus.back/tmp-files/2-Aula_3-2020-06-29T051449.762Z.webm 
        -filter_complex " 
        [0]scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2,setsar=1[0v]; 
        [1]scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2,setsar=1[1v];
        [0v][0:a][1v][1:a]concat=n=2:v=1:a=1[out]" -map "[out]" output.webm
        """
        command = 'ffmpeg -y'
        
        for file_path in file_paths:
            command += ' {} {}'.format('-i', file_path)
        
        command += ' -filter_complex "'

        for index, file_path in enumerate(file_paths):
            command += ' [{}]scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2,setsar=1[{}v];'.format(index, index)

        for index, file_path in enumerate(file_paths):
            command += '[{}v][{}:a]'.format(index, index)

        output_file = file_paths[0].split('/')[-1] # Exemplo 1-Aula_3-2020-06-29T051449.762Z.webm
        output_file = ''.join(output_file.split('-')[1:]) # Aula_3-2020-06-29T051449.762Z.webm
        output_file = os.path.join(config.UPLOAD_FOLDER, output_file)

        command += 'concat=n={}:v=1:a=1[out]" -map "[out]" {}'.format(len(file_paths), output_file)

        logger.debug("Comando a ser executado: {}".format(command))

        """
        Salvando esse arquivo finalmente na nossa base:
        """
        #size = os.stat(output_file).st_size

        new_attachment = Attachment.create(name=output_file.split('/')[-1], cdn_link=output_file, format=file.content_type, size=-1, status=ModelStatus.PROCESSING.value)
        
        threading.Thread(target=self.make_concat_async, args=(command, file_paths, new_attachment.id)).start()
        
        self.close_session()
        self._process_result = new_attachment.id

       
    def make_video_concat_async(self, 
        command:str, 
        file_paths:list, 
        attachment_id:str, 
        output_file:str, 
        *args, 
        **kwargs):

        # Executando o comando do ffmpeg        
        subprocess.call(command, shell=True)

        new_paths = []

        # Renomeando os arquivos:
        for file_path in file_paths:
            destiny_path = os.path.join(config.UPLOAD_CONCLUDED, file_path.split('/')[-1])
            os.rename(file_path, destiny_path)

            new_paths.append(destiny_path)

        logger.debug("Arquivos renomeados para: {}".format(new_paths))

        """
        Atualizando devidamente a aula
        """
        from app import create_app, db

        with create_app(with_port=False).app_context():
            Attachment.query.filter_by(id=attachment_id).update({'status': ModelStatus.ACTIVE.value})
            db.session.commit()
        
        logger.info("Processamento final do anexo '{}' concluído!".format(attachment_id))


    def make_concat_async_file_writer(self, 
        file_paths:List[str], 
        output_file_name:str,
        *args, 
        **kwargs):

        logger.info("Escrevendo o vídeo {}".format(output_file_name))

        base_path = output_file_name

        """
        1º Fazendo o "append" de todos os arquivos que não são o base neste. 

        2º Deletando todos os arquivos que foram atribuídos ao final
        """
        for file_path in file_paths:
            with open(base_path, "ab") as base_file, open(file_path, "rb") as file_to_merge:
                base_file.write(file_to_merge.read())

        for file_path in file_paths:
            os.remove(file_path)
               
        logger.info("Vídeo escrito com sucesso: {}".format(output_file_name))


    def __make_concat_async_file_writer(self, 
        file_paths:List[str], 
        output_file_name:str,
        attachment_id:str, 
        *args, 
        **kwargs):

        logger.info("Escrevendo o vídeo {}".format(output_file_name))

        base_path = output_file_name

        """
        1º Fazendo o "append" de todos os arquivos que não são o base neste. 

        2º Deletando todos os arquivos que foram atribuídos ao final
        """
        for file_path in file_paths:
            with open(base_path, "ab") as base_file, open(file_path, "rb") as file_to_merge:
                base_file.write(file_to_merge.read())

        for file_path in file_paths:
            os.remove(file_path)

        """
        Atualizando devidamente a aula
        """
        from app import create_app, db

        # Pegando o tamanho do arquivo consolidado:
        size = os.stat(base_path).st_size

        with create_app(with_port=False).app_context():
            Attachment.query.filter_by(id=attachment_id).update({'status': ModelStatus.ACTIVE.value, 'size': size})
            logger.info("Processamento do anexo '{}' concluído!".format(attachment_id))
            db.session.commit()
        
        logger.info("Vídeo escrito com sucesso: {}".format(output_file_name))


    def generate_ffmpeg_command(self, files:List[str], end_file:str, *args, **kwargs) -> str:
        """
        Devemos montar uma string de chamada parecida com:
        ffmpeg -i /home/pyduh/Enterprise-Projects/aula-plus.back/tmp-files/1-Aula_3-2020-06-29T051449.762Z.webm 
        -i /home/pyduh/Enterprise-Projects/aula-plus.back/tmp-files/2-Aula_3-2020-06-29T051449.762Z.webm 
        -filter_complex " 
        [0]scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2,setsar=1[0v]; 
        [1]scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2,setsar=1[1v];
        [0v][0:a][1v][1:a]concat=n=2:v=1:a=1[out]" -map "[out]" output.webm
        """
        command = 'ffmpeg -y'
        
        for file_path in files:
            command += ' {} {}'.format('-i', file_path)
        
        command += ' -filter_complex "'

        for index, file_path in enumerate(files):
            command += ' [{}]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[{}v];'.format(index, index)

        for index, file_path in enumerate(files):
            command += '[{}v][{}:a]'.format(index, index)

        command += 'concat=n={}:v=1:a=1[out]" -map "[out]" {}'.format(len(files), end_file)

        logger.debug("Comando a ser executado: {}".format(command))

        return command
