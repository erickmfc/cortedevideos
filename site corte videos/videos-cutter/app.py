import os
import subprocess
import tempfile
import datetime
import logging
from flask import Flask, request, jsonify, send_from_directory, render_template, url_for

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cortar_video(input_path, output_path, segmento_duracao, intervalo_remocao):
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        duration = float(subprocess.check_output(cmd, stderr=subprocess.PIPE).decode('utf-8').strip())
        logger.info(f"Duração do vídeo: {duration} segundos")

        segments = []
        for start_time in range(0, int(duration), segmento_duracao):
            end_time = min(start_time + segmento_duracao, duration)
            segment_duration = end_time - start_time

            if segment_duration <= intervalo_remocao:
                logger.info(f"Segmento iniciando em {start_time} é menor ou igual ao intervalo de remoção. Ignorando.")
                continue

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_segment:
                segment_output = temp_segment.name
                cut_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-t", str(segment_duration - intervalo_remocao),
                    "-i", input_path,
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    segment_output
                ]
                subprocess.run(cut_cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE) # Captura stdout
                segments.append(segment_output)
                logger.info(f"Segmento cortado: {segment_output}")

        if segments:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as tmpfile:
                for segment in segments:
                    tmpfile.write(f"file '{segment}'\n")
                temp_filename = tmpfile.name

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            final_output_path = f"{output_path}_{timestamp}.mp4"

            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", temp_filename,
                "-c", "copy",
                final_output_path
            ]
            subprocess.run(concat_cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE) # Captura stdout
            logger.info(f"Vídeo concatenado: {final_output_path}")
            os.unlink(temp_filename)

            for segment in segments:
                os.remove(segment)

            return final_output_path
        else:
            logger.warning("Nenhum segmento gerado. Nenhum vídeo concatenado.")
            return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Erro no ffmpeg: {e}")
        if e.stderr:
            logger.error(f"Stderr do ffmpeg: {e.stderr.decode()}")
        if e.stdout:
            logger.error(f"Stdout do ffmpeg: {e.stdout.decode()}")
        return None
    except ValueError:
        logger.error("Erro: Duração do vídeo inválida.")
        return None
    except Exception as e:
        logger.exception("Um erro inesperado ocorreu:")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video = request.files.get('file')
        if not video or not allowed_file(video.filename):
            return jsonify({'error': 'Arquivo inválido ou não enviado. Envie um arquivo de vídeo válido.'}), 400

        segmento_duracao = request.form.get('segmento_duracao')
        intervalo_remocao = request.form.get('intervalo_remocao')

        try:
            segmento_duracao = int(segmento_duracao)
            intervalo_remocao = int(intervalo_remocao)
            if intervalo_remocao >= segmento_duracao: # Nova validação
                return jsonify({'error': 'O intervalo de remoção deve ser menor que a duração do segmento.'}), 400
        except ValueError:
            return jsonify({'error': 'Os campos de duração e intervalo devem ser números inteiros.'}), 400

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video.filename)[1]) as temp_video:
                video.save(temp_video.name)
                input_path = temp_video.name
                output_base_path = os.path.join(app.config['OUTPUT_FOLDER'], os.path.splitext(os.path.basename(video.filename))[0])

                output_path = cortar_video(input_path, output_base_path, segmento_duracao, intervalo_remocao)

                if output_path:
                    filename = os.path.basename(output_path)
                    return jsonify({
                        "message": "Vídeo cortado com sucesso!",
                        "download_link": url_for('download_file', filename=filename)
                    })
                else:
                    return jsonify({'error': 'Erro durante o corte do vídeo. Verifique os logs.'}), 500
        except Exception as e:
            logger.exception("Erro no processamento do vídeo:")
            return jsonify({'error': 'Erro inesperado durante o upload ou processamento do vídeo.'}), 500
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if os.path.exists(filepath):
        absolute_path = os.path.abspath(app.config['OUTPUT_FOLDER']) # Caminho absoluto
        logger.info(f"Enviando arquivo para download: {filepath}")
        return send_from_directory(absolute_path, filename, as_attachment=True)
    else:
        logger.error(f"Arquivo não encontrado para download: {filepath}")
        return jsonify({'error': 'Arquivo não encontrado para download.'}), 404

if __name__ == '__main__':
    app.run(debug=True)