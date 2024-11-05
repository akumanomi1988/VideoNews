import json
from scripts.AI.text_to_speech import TTSEdge

class test:
    def __init__(self, config_file='settings.json'):
        self.config_file = config_file
        self.config = self.load_configuration()
        self.temp_dir = self.config['settings']['temp_dir']
        self.tts = TTSEdge(output_dir=self.temp_dir)
        self.video_files = []
    def load_configuration(self):
        """Load the configuration from the specified JSON file."""
        with open(self.config_file, 'r') as file:
            config = json.load(file)
        return config
if __name__ == "__main__":
    t = test()
    text = f'''Bienvenidos a este informativo especial. Hoy nos encontramos analizando los recientes ataques del expresidente Donald Trump hacia figuras clave de la política estadounidense. En su más reciente mitin en Michigan, Trump no solo dirigió su ira hacia la excongresista Liz Cheney, sino que también arremetió con dureza contra su antiguo asesor de seguridad nacional, John Bolton.
        Trump se refirió a Bolton como "un idiota" y "un loco", afirmando que le era útil tenerlo en la misma sala durante reuniones con líderes extranjeros. Según sus palabras, no necesitaba ser duro en estas negociaciones porque la presencia de Bolton, descrito en términos muy despectivos, era suficiente para intimidar a los mandatarios y hacer que accedieran a sus demandas. Trump recordó también que fue Bolton, junto con Dick Cheney, quienes impulsaron la invasión de Estados Unidos a Medio Oriente durante la presidencia de George W. Bush. Sin embargo, el expresidente se jactó de haber conseguido sus objetivos gracias a que los líderes extranjeros pensaban que estaba “loco”.
        Minutos después, en el estudio de noticias, John Bolton, quien también fue asesor de seguridad nacional en la administración de Trump, respondió a estos ataques. Con calma, Bolton comentó que le parecía curioso que Trump todavía lo tuviera en mente y calificó los comentarios como infantiles, criticando la incapacidad de Trump para sostener un debate sobre política sin recurrir a insultos personales. Bolton añadió que estos ataques eran una muestra de por qué considera que Trump no está calificado para el liderazgo.
        En un momento de la conversación, el presentador y Bolton se detienen a analizar la particular forma en que Trump atacó a Liz Cheney. El expresidente, en Michigan, describió a Cheney como si estuviese en una situación de combate, con nueve rifles apuntándole. Bolton advirtió que este tipo de retórica violenta es típica de Trump cuando se enfrenta a críticos. Según Bolton, el motivo de fondo para estas agresiones verbales es que Cheney votó en su contra durante el proceso de destitución tras los disturbios del 6 de enero. Esto, dice Bolton, es una herida que Trump no puede dejar atrás.
        La entrevista continuó abordando las contradicciones de Trump en su política exterior, recordando cómo mantuvo tropas en Irak y Siria, y autorizó el ataque contra el general iraní Qasem Soleimani, mientras criticaba a otros por tener posiciones similares a las suyas. Bolton destacó que Trump rara vez asume responsabilidades, señalando que incluso el criticado acuerdo de retirada de Afganistán fue impulsado por el propio Trump y el entonces secretario de Estado Mike Pompeo. Pese a las críticas de Trump hacia el presidente Joe Biden, Bolton recordó que fue este acuerdo de la administración Trump el que obligó a Biden a tomar la difícil decisión de continuar con el proceso de retirada.
        Finalmente, en un tono más serio, el presentador le preguntó a Bolton si creía que Trump aceptaría los resultados de las próximas elecciones en caso de perder. Bolton fue claro: no cree que Trump lo haga. Agregó que este patrón de comportamiento ya se evidenció en 2020, cuando Trump impugnó los resultados tras conocer que había perdido. La posibilidad de nuevos litigios ya está sobre la mesa, y Bolton advirtió que, aunque las demandas previas a la elección pueden ayudar a clarificar ciertos puntos, la negativa de Trump a aceptar una derrota sigue siendo un riesgo. 
        Así se desarrolla esta polémica en torno a Donald Trump, quien se encuentra en el centro de atención por sus ataques a antiguos colaboradores y críticos dentro de su propio partido. Desde aquí, continuaremos informando sobre la controversia y sus implicaciones en el ámbito político estadounidense.'''

    a = t.tts.text_to_speech_file(text,'en','es-AR-ElenaNeural - es-AR (Female)') 