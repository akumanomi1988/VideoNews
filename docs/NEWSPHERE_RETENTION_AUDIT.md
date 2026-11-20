# Auditoría de montaje de NewSphere · 20 de noviembre de 2026

Ocho MP4 locales, sus proyectos y los límites acústicos originales. Los primeros
30 segundos se reconstruyeron con las palabras cuyo inicio es anterior a 30 s.
El fichero de evidencia local `output/retention-audit/baseline.json` contiene
las aperturas completas, los tiempos por escena, la narración por escena y el
empaquetado guardado. La hoja de contacto toma fotogramas a 3, 11, 22 y 70 s,
y a ocho segundos del final. Las pausas se midieron entre palabras alineadas.
Los WAV de audición permiten valorar pronunciación y prosodia por separado.
Los datos del canal no se usaron para atribuir causalidad.

| Episodio | Máster | Recursos únicos | Planos medianos | Gráficos animados | Mayor pausa entre palabras |
| --- | ---: | ---: | ---: | ---: | ---: |
| GTA VI | 203,1 s | 8 | 25,4 s | 2 | 0,60 s |
| Compraventas INE | 216,3 s | 9 | 24,2 s | 2 | 0,62 s |
| Salario mínimo | 231,3 s | 12 | 19,4 s | 0 | 0,68 s |
| Programa de Vox | 217,8 s | 9 | 24,4 s | 2 | 0,72 s |
| Debate económico | 226,6 s | 10 | 22,7 s | 1 | 0,65 s |
| Rebaja de carburantes | 210,1 s | 10 | 20,7 s | 2 | 0,60 s |
| Vivienda y empleo | 226,2 s | 12 | 19,1 s | 1 | 0,64 s |
| Ayudas DANA Adam | 203,9 s | 9 | 22,9 s | 2 | 0,86 s |

## Observaciones por episodio

- **GTA VI.** «La edición básica de PlayStation cuesta casi ochenta euros en
  España» y «treinta imágenes por segundo» concretan el título. A 3, 11 y 22 s
  se mantiene la caja registradora de la miniatura. Podría exhibir precio
  y fluidez como dos momentos separados. El gráfico de fechas sí progresa.
  El cierre formula un criterio de compra y termina con una invitación genérica.
  Es una excepción temática frente a la especialización del canal.
- **Compraventas.** «El dato cuenta llaves que cambian de manos» hace accesible
  la diferencia entre operaciones y precios. La misma llave ocupa los tres
  primeros fotogramas de muestra. El 13,4 % del título sigue pendiente al
  llegar a 30 s. Adelantarlo y mostrar operaciones frente a precio evitaría
  que la llamada a la acción interrumpa el arranque.
- **Salario mínimo.** «El titular anuncia 65 euros más por paga» entrega una
  cifra, pero a continuación se enumeran tres preguntas y se pide suscripción.
  A 22 s aparece un nuevo recurso, aunque ninguno de los 12 tiene animación
  semántica registrada. Convertir bruto, complementos y retenciones en capas
  de una nómina permitiría seguir la explicación. El cierre contiene una lista
  práctica, pero no ofrece un siguiente vídeo sobre empleo.
- **Vox.** Llaves y solicitud distinguen compra y acceso a vivienda pública.
  Aparecen el saludo y una CTA antes de entrar en los detalles, y la misma
  imagen se mantiene en los tres puntos iniciales. Anticipar una propuesta
  concreta y rotular su condición de propuesta haría más preciso el contrato
  del título. La descripción conserva las fuentes electorales.
- **Debate económico.** «Cincuenta mil euros de salario medio y un millón de
  viviendas» abre sin saludo. La metáfora de las instrucciones de montaje
  sostiene el cierre. A 22 s ya aparece un gráfico, pero muestra participantes
  antes de contrastar los supuestos de sus promesas. El título omite las cifras
  que hacen concreta la apertura.
- **Carburantes.** «Los veinte céntimos siguen en diciembre» entrega la noticia
  de inmediato. El surtidor y después un documento acompañan el cambio de
  explicación. El título reserva espacio a «ojo con esto» que podría anticipar
  la distinción entre impuesto y precio final. El cierre da instrucciones
  prácticas y tiene relación editorial con futuros episodios de consumo.
- **Vivienda y empleo.** «Puedes conseguir trabajo y seguir sin poder mudarte»
  da una consecuencia relatable. A 22 s ya hay un segundo recurso; la CTA
  precede a la explicación del mecanismo. Conectar alquiler, mudanza y empleo
  a medida que se nombran daría un motivo a cada cambio visual. Tiene continuidad
  potencial con compraventas y el salario mínimo.
- **DANA Adam.** La persiana intacta con acceso cerrado es una hipótesis
  explícita que vuelve al final. No cambia de ilustración en las tres muestras
  iniciales y los importes aparecen más tarde. La descripción y los gráficos
  atribuyen la medida a la norma. El A/B local reutiliza este máster como
  control y superpone avisos sincronizados, sin reescribir la voz original.

## Qué estaba aplicado

- Studio versiona guion y storyboard. FFmpeg sincroniza escenas con límites
  acústicos y GraphicsEngine resuelve animaciones contra esos límites.
- Studio verifica códecs, duración, resolución, decodificación y correspondencia
  de recursos. La transición visual suele ser un fundido y cada escena tiene
  un recurso principal. Estos controles no comprueban la relación editorial
  de cada frase con la imagen.
- La plantilla de saludo y CTA estaba en las instrucciones y se observa en
  seis de las ocho aperturas. El montaje y la voz no validaban ese ritmo
  editorial. Las miniaturas y descripciones del corpus se conservan en los
  proyectos. Dentro de este corpus no consta una pantalla final interactiva
  verificada.

Las medidas de volumen, pausas y alineación no permiten juzgar expresividad,
acento o fatiga. Las cifras de actividad de prueba no permiten inferir
retención orgánica. El A/B local compara el montaje, no el rendimiento del canal.
