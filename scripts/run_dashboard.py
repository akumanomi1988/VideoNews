from flask import Flask
from dashboard import create_app
import logging
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Obtener el directorio de métricas desde una variable de entorno o usar el valor por defecto
        metrics_dir = os.getenv('METRICS_DIR', 'metrics')
        
        # Asegurarse de que el directorio de métricas existe
        os.makedirs(metrics_dir, exist_ok=True)
        
        # Crear la aplicación Flask con la configuración especificada
        app = create_app(metrics_dir)
        
        # Configurar el host y puerto
        host = os.getenv('DASHBOARD_HOST', 'localhost')
        port = int(os.getenv('DASHBOARD_PORT', 5000))
        
        logger.info(f"Iniciando dashboard en http://{host}:{port}")
        
        # Ejecutar la aplicación
        app.run(
            host=host,
            port=port,
            debug=False  # Deshabilitar modo debug en producción
        )
    except Exception as e:
        logger.error(f"Error al iniciar el dashboard: {e}")
        raise

if __name__ == '__main__':
    main()