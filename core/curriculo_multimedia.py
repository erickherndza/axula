# -*- coding: utf-8 -*-
"""
Currículo oficial del Bachillerato en Arte Multimedia — MINERD
Extraído del Plan de Estudios oficial de la Dirección de Modalidad en Artes.
Segundo Ciclo del Nivel Secundario (4to, 5to, 6to).

Este módulo provee los saberes oficiales por asignatura para inyectar en
los prompts de IA al generar planificaciones ABP, garantizando fidelidad
con la plantilla MINERD (95-98%).
"""

# Las 7 Competencias Fundamentales oficiales (Ord. 04-2023 MINERD)
# Estas SIEMPRE se inyectan tal cual, no las genera la IA (evita duplicados)
COMPETENCIAS_FUNDAMENTALES = [
    "Competencia Ética y Ciudadana",
    "Competencia Comunicativa",
    "Competencia Pensamiento Lógico, Creativo y Crítico",
    "Competencia Resolución de Problemas",
    "Competencia Científico-Tecnológica",
    "Competencia Ambiental y de la Salud",
    "Competencia de Desarrollo Personal y Espiritual",
]

# Las 4 fases del ABP — siempre fijas (Modalidad en Artes MINERD)
FASES_ABP = [
    "Exploración e Investigación",
    "Diseño y Planificación",
    "Desarrollo y Construcción",
    "Presentación y Evaluación",
]

# Elementos STEAM — la IA debe incluir los 5 en cada fase
ELEMENTOS_STEAM = ["Ciencia", "Tecnología", "Ingeniería", "Arte", "Matemática"]

# Currículo oficial por asignatura — Bachillerato en Arte Multimedia
# Fuente: Plan de estudio de la Mención Arte Multimedia,
#         Dirección de la Modalidad en Artes, MINERD.
CURRICULUM_MULTIMEDIA = {
    'Animación': {
        "modulo": 'Competencias 9 Competencia Ética y Ciudadana',
        "horas": '4',
        "introduccion": 'De acuerdo a la etimología de la palabra animación proviene del latín, lexema «anima» que signifique «alma». Por tanto, la acción de animar se debería traducir como «dotar de alma», refiriéndose a todo aquello que no la tuviera. Pero en términos más concretos la animación es un proceso que consiste en dar la sensación de movimiento usando una secuencia de imágenes ubicándolas en una línea de tiempo. Estas secuencias de imágenes pasan rápido y nuestra retina graba cada una, creando la ilusión de una continuidad en el movimiento, sin advertir las transiciones de una imagen a otra, a este fenómeno se le ha llamado persistencia de la visión. La rama del arte que más se ha aprovechado de este hecho ha sido el cine. Hoy en día, darles alma y vida a personajes o personalidad a objetos inanimados es un arte encarnado en la animación tradicional, el stop motion y en medios digitales que ayudan o facilitan la creación. La animación 2D y 3D son las vertientes a desarrollar en esta asignatura donde el estudiante logra comprender los principios de la animación en el mundo digital y profundiza en estos principios llegando a realizar animaciones adecuadas con las herramientas utilizadas. DESARROL',
        "elemento_competencia": 'Anima, dibujos, objetos y personajes de manera tradicional y digital 2D y 3D, comprendiendo el tiempo y espacio, a través, del uso de los key frames, las principales herramientas de After Effects y la edición de videos en Premiere, creando el rigging, aplicando el blend shapes, y añadiendo movilidad en los gestos y todo el cuerpo en Maya o 3Dmax.',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
            'Planificar el movimiento de manera tradicional.',
            'Crear la estructura interna con sus articulaciones del personaje para stop motion.',
            'Desarrollar todo el exterior y detalles del personaje para stop motion.',
            'Jugar con el objeto, recreando su personalidad, voz y movimiento.',
            'Preparar conceptualmente las actitudes y personalidad del personaje.',
            'Usar la cámara fotográfica y el Dragon frame en la captura fotográfica para el stop motion.',
            'Dibujar el personaje para animación tradicional.',
            'Planificar de la animación tradicional y el dibujo cuadro a cuadro.',
            'Desarrollar la estructura interna y las articulaciones en el desarrollo de personajes.',
            'El plantear el personaje dibujado frontalmente, lateral y 3/4 (el model sheet), agregar detalles y el color en photoshop.',
            'Aplica colores, texturas, contrastes, el fondo y su profundidad, luces y sombras con la tableta gráfica y After Effects.',
            'Aplicar el 3D layer, luces, animación de las cámaras de After Effects.',
            'Crear figuras con polígonos primitivos en 3D y modela otros objetos a partir de esta, texturiza, aplica luces en Maya (o 3Dmax).',
            'Aplicar los key frames del objeto haciendo animaciones sencillas, anima cámaras y renderiza en Maya (o 3Dmax).',
            'Elaborar conceptualmente un personaje, dibujando el model sheet de frente y lateral para ser aplicado en Maya (o 3Dmax).',
        ],
        "actitudinales": [
            'inclinación por la observación y orden.',
            'Interés por la descripción.',
            'Desarrollo de habilidades creativas.',
            'Prudencia, respeto por los procesos de creación.',
            'Aptitud positiva por la animación y todos sus procesos.',
            'Interés por el espacio 2D y 3D, creación del movimiento.',
            'Interés por los efectos visuales. Actividades y estrategias de aprendizaje sugeridas:',
            'Exposición oral y audiovisual: en los diversos temas comprendidos en los contenidos presentar exposiciones y video que ejemplifiquen los conceptos impartidos en el aula.',
            'Método de proyecto: : Para el proyecto final el estudiante crea su portafolio con los resultados de todo el año escolar, este es post producido, editado y se le agrega sonido',
            'Método de preguntas: que afiancen el aprendizaje respecto a los conceptos, características, identificación, clasificación, pautas para el buen desarrollo de una animación.',
            'Aprendizaje basado en problemas: Los estudiantes combinan la animación 2D y 3D usando las herramientas de After Effects y Maya (o 3Dmax).',
            'Juego de roles: el estudiante explica a sus compañeros el método aprendido y sus diversas etapas.',
            'Panel de Discusión: al finalizar una jornada se discute sobre los avances obtenidos.',
            'Técnicas de producción creativa: 5. Lluvia de ideas: técnicas utilizadas de forma grupal para generar o producir ideas. 6. Análisis morfológico: es útil para descomponer un problema en sus elementos más básicos, creando una matriz que facilita la combinación aleatoria de las distintas posibilidades existentes en cada uno de ellos.',
            'Visita: Visitas a museos, galerías y actividades relacionadas con arte y la cultura de forma presencial o haciendo uso de entornos virtuales Evaluación: Resultados del Aprendizaje Criterios de evaluación Técnicas e Esperados instrumentos de evaluación 1. Analiza la historia y x Explica la historia y x Participación evolución de la animación evolución de la activa para una mejor aplicación animación. mediante de las técnicas. preguntas y',
        ],
        "indicadores": [
            'Conceptos básicos de la edición hechos de carácter histórico, relativo a (Lineal y no-lineal) y el montaje. la producción y post producción.',
            'Teoría del vídeo, y sus soportes en las x Conoce funciones y herramientas de distintas fases de postproducción softwares de edicion (Adobe Premier) audiovisual. y las aplica de forma correcta a la hora',
            'Realización de materiales de realizar un proyecto audiovisual. audiovisuales según las características x Identifica y aplica las diferentes del proyecto y software a utilizar. técnicas y géneros audiovisuales.',
            'Técnicas básicas de edición de sonido. x Realiza producciones con un orden',
            'Códecs y formatos de audio para logico y organizado a través de efectos proyectos audiovisuales. secuenciales y tecnicasvideográficas.',
            'Aplicación de la tecnología del sonido x experimenta la apreciacion musical y en los soportes de la multimedia. acustica y su historia.',
            'Procedimentales: x aplicatecnicas de edicion digital de',
            'Manejar de Softwares de edición de audio y procesamiento del sonido. audio. x Crea Foley, efectos digitales y',
            'Interactuar con el software de musicalizacion mediante softwares edición.',
            'Crear y desglosar pasos a seguir para especiales para sonido (Adobe la creacion de una banda sonora. audition)',
            'Elaborar grabaciones, captura y x desarrollar proyectos de captura de edicion de audio para posterior audio y creacion de bandas sonoras, asi proyecto. como mezcla y diseño de sonidos para cualquier audiovisual. Procedimentales:',
            'Identificar y diferenciar las vertientes o metodos de edicion y montaje.',
            'Interactuar con el software de edición.',
            'Crear y desglosar pasos a seguir para la edición.',
            'Elaborar proyectos audiovisuales. Actitudinales:',
        ],
    },
    'Diseño Básico y Expresión Visual': {
        "modulo": 'Formación',
        "horas": '4',
        "introduccion": 'La asignatura diseño básico y expresión visual permite al estudiante conocer los elementos básicos de la comunicación visual, promueve en el estudiante la planeación antes de la generación de formas utilizando modelos de solución de problemas. A través de ejercicios teórico-prácticos el estudiante podrá identificar los conceptos básicos de comunicación, los elementos conceptuales del diseño y modelos de solución de problemas en la generación de formas. Los conocimientos adquiridos servirán como base a los demás módulos. El estudiante de diseño básico y expresión visual es creativo, aplica modelo de solución de problemas para crear mensajes gráficos y comunicar ideas en superficies de dos dimensiones integrando elementos básicos de formas (punto, línea, plano, color, textura, etc.)',
        "elemento_competencia": 'Emplea atributos físicos y visuales de la forma en la creación de mensajes gráficos, aplicando modelos de resolución de problemas en la generación de mensajes gráficos. Resultados de Aprendizaje Esperados: 1) Describe los elementos básicos de la forma y su uso como expresión visual. 2) Experimenta y representa imágenes en ilustraciones realísticas y abstractas utilizando punto, línea, plano y formas. 3) Crea comunicaciones efectivas por medio de figuras y formas. 4) Aplica método de solución de problemas de diseño como modelo de generación de formas. CONTENIDOS: Conceptuales: I. Concepto y cla',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
        ],
        "actitudinales": [
        ],
        "indicadores": [
        ],
    },
    'Diseño Web': {
        "modulo": 'Formación Para diseño y creatividad multimedia (DCM. 2)',
        "horas": '6',
        "introduccion": 'La asignatura Diseño Web permite al estudiante modificar la apariencia de documentos HTML utilizando instrucciones de hoja de estilos en cascada (CSS), creando sitios más atractivos, además de tener control sobre la distribución y composición de elementos y contenidos de un sitio web. A la vez que permite crear transiciones y añadir animación. La asignatura ofrece al estudiante una visión general sobre el proceso de diseño y conceptualización de una página o plataforma web, con los cuales poner en práctica los conocimientos adquiridos que les servirá de carta de presentación ante futuras oportunidades laborales. De igual modo se persigue que el estudiante obtenga conocimientos fundamentales para la publicación y construcción de sitios web a partir de criterios personalizados mediante el empleo de gestores de contenido. Profundizar en los procesos y herramientas para planificación, diseño e implementación de contenidos web multimedia que consoliden la experiencia de usuario. Elemento de competencia: Aplica los lenguajes de maquetación para el desarrollo e interactividad de sitios web empleando los lenguajes de programación html y css.',
        "elemento_competencia": 'Aplica los lenguajes de maquetación para el desarrollo e interactividad de sitios web empleando los lenguajes de programación html y css.',
        "rae": [
            'Explica de manera x Modifica apariencia, color, x Cuestionario oral y escrita cómo tipografía, despliegue y x Tareas escribir instrucciones x Proyecto. visibilidad de elementos CSS. x Revisión de HTML. pares.',
            'Diseña documentos x Modifica posición y x Presentación para diferentes x Video tutoriales. espacios de elementos navegadores x Proyecto html utilizando estilos CSS',
            'Estiliza tablas y crean x Modifica apariencia y x Presentación. barras de navegación x Proyecto. espacios de tablas utilizando estilos CSS',
            'Integra animaciones y x Aplica animación y x Presentación. efectos de transición a transiciones a documentos Explicación. elementos html mediante estilos css html Proyecto.',
        ],
        "conceptuales": [
            'Concepto de publicidad.',
            'Origen y evolución de la publicidad.',
            'Terminología publicitaria',
            'Responsabilidad social y ética de la publicidad.',
            'Clasificación de la publicidad.',
            'Rol de la agencia publicitaria',
            'Estructura interna, organigrama y flujograma de la agencia publicitaria.',
            'Planos de la cámara.',
            'Transiciones visuales.',
            'Iluminación',
            'Dirección de arte',
            'Libro de producción',
        ],
        "procedimentales": [
            'Delimita el perfil del publico objetivo.',
            'Redacta el brief.',
            'Presupuesto publicitario.',
            'Realiza los parsos para el funcionamiento de la cámara de grabación.',
            'Aplica los términos técnicos en la producción audiovisual: movimientos de la cámara, enfoque, diafragma, encuadre y foco.',
        ],
        "actitudinales": [
            'Fomento de la actitud responsable.',
            'Fomento de la planificación.',
            'Fomento de la creatividad.',
            'Desarrollo de la comunicación por medio del audio y video.',
            'Fomento del trabajo en equipo.',
        ],
        "indicadores": [
        ],
    },
    'Edición, Sonido y Musicalización': {
        "modulo": 'Formación Post Producción',
        "horas": '4',
        "introduccion": 'Edición de Video, permite al estudiante conocer sobre los principios básicos del montaje como también de la edición digital, así como los métodos necesarios para iniciar un proceso de post producción, utilizando herramientas digitales (softwares) para crear cualquier proyecto audiovisual. Desde el punto de vista del lenguaje audiovisual el montaje o edición, es el proceso de ordenación de un material con el fin de obtener un programa continuado, sin imágenes o sonidos inútiles o mal colocados. En tal sentido aplicaremos estos conceptos y fundamentos en programas de edición, a fin de lograr un trabajo audiovisual con técnicas videográficas desarrolladas profesionalmente por el alumno. Asimismo, las Producciones Audiovisuales se basan en dos puntos fundamentales: el audio y el video. ¿El Sonido es un efecto de captación de gran importancia en los medios de comunicación; Un 40% en la televisión y un 100% en la radio. La materia de Producción de Sonido y Musicalización es esencial para enseñar a optimizar técnicas y lograr en el alumno una habilidad, que es el de estimular y cautivar en una forma creativa con música y sonidos los mensajes publicitarios, jingles o cualquier trabajo audi',
        "elemento_competencia": 'Post producción (PP 1.2) Elemento de Competencia Realiza producciones audiovisuales como cortos, comerciales y spots de radio y television, que conlleve el montaje de banda sonoras, Efectos visuales, edicion de video y eleccion de tecnicas y genero a desarrollar en el mismo.',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
        ],
        "actitudinales": [
        ],
        "indicadores": [
            'Etapas de elaboración de una producción desde la creacion de guion, audiovisual: Pre producción, Producción y hasta la eleccion de tomas e Post producción. imagenes para la post',
            'Desarrollo del storyline y el storyboard. produccion.',
            'Tipos de proyectos audiovisuales.',
            'Emprendimiento y empleabilidad de',
            'Elabora conceptos de proyecto. musicalizacion y banda Procedimentales: Sonora aplicando los principios de edicion de',
            'Crear y desglosar las etapas para desarrollar el audio para cualquier tipo de proyecto audiovisual. genero audiovisual.',
            'Interactuar con el software de edición de audio y video. x Realiza producciones',
            'Elaborar grabaciones, captura y edicion de audio y audiovisuales como cortos, video para posterior montaje. comerciales y spots de radio',
            'Elaborar propuesta de distribucion del material final. y televisión. Actitudinales:',
            'Creatividad.',
            'Organización y previsión.',
            'Responsabilidad',
            'Fomento de la calidad en la entrega y presentacion.',
        ],
    },
    'Fotografía': {
        "modulo": 'Formación Para diseño y creatividad multimedia',
        "horas": '4',
        "introduccion": 'La fotografía es una asignatura que demanda la asimilación de conocimientos y desarrollo de habilidades y actitudes proporcionándole al estudiante el dominio de conocimientos teóricos y técnicos. En la misma se dedarrollaran las temáticas: inicios históricos de la fotografía, así como los componentes de una cámara fotográfica y su uso adecuado cuales son las técnicas y leyes de la fotografía, así como los ángulos y planos fotográficos y sus usos adecuados. De esta forma, analiza la relación de la fotografía con el arte y la función social de la imagen haciendo uso de la fotografía como medio de expresión de comunicación.',
        "elemento_competencia": 'Ejecuta el proceso del uso de la cámara fotográfica, en proyectos de expresión artística y como medio de comunicación aplicando técnicas novedosas y creativas teniendo como base los recursos técnicos y de composición. Resultados de aprendizaje esperados: 1 Aplica los principios básicos de la fotografía por medio de estrategias creativas 2 Explica antecedentes y evolución de la fotografía. 3 Realiza fotografías técnicamente correctas. 4 Maneja la cámara de manera correcta. 5 Identifica los mecanismos adecuados para ser usados dependiendo el tipo de iluminación. 6 Valora la fotografía como medio',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
            'Aplica hojas de estilos internas y externas a documentos html.',
            'Modifica color de elementos html.',
            'Distingue las distintas notaciones de color',
            'Aplica tipos de letras externas',
            'Controla y modifica posición de elementos html',
            'Uso de editores de texto para crear documentos javascript',
            'Integras guiones (script) a documentos html',
            'Validación de estilos',
        ],
        "actitudinales": [
            'Planificación.',
            'Trabajo en equipo.',
            'Responsabilida.',
            'Emprendimiento.',
        ],
        "indicadores": [
        ],
    },
    'Guion': {
        "modulo": '',
        "horas": '4',
        "introduccion": 'Guion es una asignatura que permite al estudiante identificar el proceso de construcción de guiones para diferentes tipos de guiones tanto literario como técnico y su evolución y adaptación a la producción audiovisual (spot, animación, cortometraje, programas de radio y televisión); conocer estructuras y estilos de expresión literaria a fin de que pueda elaborar su propio guion, En ese sentido, se estudiarán las técnicas utilizadas por Syd Field, Christopher Vogler, Linda Seger y Robert McKee para crear historias. El estudiante podrá identificar ideas para elaborar guiones utilizando un lenguaje adecuado. Prepara al estudiante para medir y estructurar una historia. Propone que el alumno planifique y redacte guion literario y luego un guion técnico con soluciones audiovisuales para diferentes formatos, soportes y medios de comunicación. La escritura de un guion técnico está íntimamente relacionada con la producción del audiovisual. Tanto el guionista como el productor de material audiovisual deben saber interpretaron guion, reconocer su estructura, estilo, sus personajes funciones y conflictos. Esta asignatura desarrolla en el alumno un pensamiento creativo y reflexivo en relación a',
        "elemento_competencia": 'Construye un guion que funciona de soporte o base para las produciones audiovisuales tomando en cuenta los fundamentos y elementos que componen el guión literario y técnico.',
        "rae": [
            'Realiza un guión literario cumpliendo con las características: Detalla el contenido de cada escena y cada secuencia.',
            'Expresa una línea argumental con un planteamiento, desarrollo y desenlace dentro de la estructura general del film.',
            'Identifica diversos tipos de guiones (cine, radio y televisión)',
            'Reconoce los elementos adecuados para para cada tipo de guion.',
            'Redacta guiones para cine.',
            'Hace escaletas (guiones) para radio.',
            'Confección a escaletas (guiones) para TV.',
            'Maneja el lenguaje adecuado para llevarlo a la práctica audiovisual.',
            'Identifica diversos tipos de guiones técnicos',
            'Redacta diversos tipos de guiones técnicos para cine.',
            'Maneja el lenguaje adecuado para llevarlo a la práctica audiovisual.',
            'Expone su guion a través de presentación de diapositivas.',
        ],
        "conceptuales": [
            'Característica del guion literario y técnico.',
            'Identificación de guion estructurado para cine, radio y televisión',
            'Técnicas de enseñanza de guiones: Syd Field, Christopher Vogler, LindaSeger y Robert McKee. Procedimentales:',
            'Describir características de guión literario',
            'Describir características de guión Técnico',
            'Redacta con fluidez texto para guiones sin faltas ortográficas.',
            'Reconoce e identifica una buena idea',
            'Creación de historias',
            'Descripción de personajes principales y secundarios',
            'Elaboración destorylines',
            'Redacción guion correspondiente a una historia',
            'Análisis de historias',
            'Comparación de historias para distinguir los puntos fuertes y débiles a cuanto la originalidad.',
            'Crea Programas de TV y Radio',
            'Redacta con fluidez y buena ortografía',
        ],
        "procedimentales": [
        ],
        "actitudinales": [
            'Ético profesional al uso de su guion.',
            'Curiosidad por la investigación.',
            'Perfeccionamiento de la redacción.',
            'Redacta con fluidez y buena ortografía.',
            'Distingue una buena idea.',
            'Crea historias.',
            'Describe personajes principales y secundarios.',
            'Hace el guion técnico correspondiente a esa historia.',
            'Analizar historias de cine.',
            'Desarrollo de la creatividad. Actividades y estrategias de aprendizaje sugeridas: 1) Actividades y estrategias de aprendizaje: 2) Explica en clase las diversas técnicas que existen para la realización de un Guion. 3) Descripción de concepto o idea 4) Descripción deconflicto dentro de la historia. 5) Investigación de distintas técnicas para elaboración de guion literario. Enumera los elementos necesarios para estructurar un guion literario. 6) Análisis de elementos de la estructura de guión. 7) Identifica diferentes medios y formatos. 8) Combina elementos. 9) Elabora un storyline. 10) Experimenta con diferentes técnicas. 11) Representa gráficamente una historia. 12) Creaescaletas (guiones) para televisión. 13) Identifica elementos para estructura de guion de television. 14) Describe las técnicas más adecuadas para redactar guion de televise. 15) Redacción de guión. 16) Desarrolla su creatividad a través de la narrativa guionizada. 17) Realización de ejercicio narrando historias o cuentos puestos en escena (spots, cortometrajes, animaciones, etc.) 18) Aplica técnicas y recursos para narrar historias. 19) Analiza y compara historias. 20) Crean escaletas (Guiones) de programas para radio. 21) Identifica elementos para estructura de guion de radio. 22) Describe las técnicas más adecuadas para redactar de guion para radio. 23) Redacta guion para radio. Evaluación: RAE Criterios de evaluación Técnicas e instrumentos de Resultados del evaluación Aprendizaje Esperados 1. El estudiante expone oralmente su cuento',
            'Criterios de Evaluación: o historia. x Trabajos o tarea',
            'Redacta un guion de 2. Enumera los acuerdo a las técnicas x Elaboración de guion elementos aprendidas. necesarios para literario. estructurar un guion',
            'Presentación en literario.',
            'Estructura el contenido en clase. base a cada una de las técnicas aprendidas. x Análisis de guion 3. Redacta diversos tipos de guiones. literario.',
            'Analiza cada uno de los x Grabaciones 4. Describe las elementos de su estructura diferentes técnicas para lograr una buena idea audiovisuales que existen para la en su contenido. x Guía de observación. realización de un x Simulaciones',
        ],
        "indicadores": [
        ],
    },
    'Historia del Arte Universal y la Estética Digital': {
        "modulo": 'Formación Artístico-Cultural',
        "horas": '4',
        "introduccion": 'La apreciación del arte universal y dominicano es la base introductoria sobre la cual se fortalecerán los aprendizajes artísticos de los estudiantes a partir del conocimiento de obras artísticas contextualizadas en las épocas y contextos históricos, sociales, políticos y religiosos. Posibilitando la interacción dialógica con la percepción de los expresiones e imágenes artísticas más representativas del arte universal y dominicano. El alumno será capaz de realizar la apreciación de obras artísticas correspondientes a movimientos y estilos artísticos de la Historia del Arte universal y dominicano, argumentando su relación con la época, el contexto socio-cultural y geográfico; a la vez que se aprecia el arte de multimedia y la estética digital proporciona al estudiante los conceptos básicos para la apreciación estética y comprensión de los elementos que constituyen una obra de arte y se realiza un análisis crítico a las manifestaciones artísticas actuales.',
        "elemento_competencia": 'Valora distintas manifestaciones artísticas para diversificar su gusto y su consumo artístico. Critica con fundamento, las manifestaciones artísticas para ser selectivo y reflexivo en su consume.',
        "rae": [
            'Valora la variabilidad de las funciones sociales y de las concepciones diferentes del arte a lo largo de la historia.',
            'Utiliza términos del glosario de forma adecuada en actividades apreciativas.',
            'Explica los hechos artísticos más relevantes de la Historia del Arte situándolos adecuadamente en el tiempo y en el espacio valorando su significación en el proceso histórico-artístico.',
            'Disfruta las obras más destacadas el patrimonio artístico dominicano, desde posiciones críticas y creativas, como exponente de nuestra identidad cultural.',
            'Desarrolla el gusto personal, el sentido crítico y la capacidad de goce estético a través de las artes.',
            'identifica y reconoce los factores que inciden en la concepción de lo bello.',
            'Valora el arte como manifestación de la belleza y expresión de ideas, sensaciones y emociones.',
            'Experimenta el arte como un hecho histórico compartido que permite la comunicación entre individuos y culturas en el tiempo y el espacio, a la vez que desarrolla un sentido de identidad.',
            'Describe la etapa de mayor desarrollo del arte digital',
            'Identifica estilos de Artes de digital.',
            'Digitaliza la expresión artística de los estudiantes. Contenidos:',
        ],
        "conceptuales": [
        ],
        "procedimentales": [
        ],
        "actitudinales": [
        ],
        "indicadores": [
        ],
    },
    'Identidad, Cultura y Emprendimiento': {
        "modulo": 'Formación Artístico-Cultural',
        "horas": '2',
        "introduccion": 'La comprensión de la sociedad en el cual el estudiante de artes se encuentra inmerso como sujeto creador, sólo es posible mediante la interacción de las disciplinas de la comunicación, la cultura y el arte, y en esta coyuntura fortalecer el conocimiento de la propia identidad. Para el joven adolescente, es fundamental plantear importantes interrogantes humanas: quién soy, cómo actúo, a dónde quiero llegar. Encontrar la razón de ser y estar cursando estudios artísticos. El artista crea y transforma la materia a partir de sí mismo y es en su propio ser donde encuentra la energía y el sello único que lo proyectará profesionalmente en un futuro. La asignatura Identidad, cultura y comunicación, se centra en el estudiante partiendo de la apropiación de sí mismo, de sus raíces, y de los procesos y tecnologías de la Comunicación que colaboran con su expresividad. Y es que en la actualidad los artistas tienen a su disposición valiosos recursos para la comunicación de sus expresiones mediante nuevas tecnologías digitales, pueden recrear su imagen y conocer a otros, en cualquier parte del mundo, actuar como agentes transformadores y enriquecedores de su cultura. En este sentido, en la actuali',
        "elemento_competencia": 'Comunica su identidad personal y social a través de un proyecto emprendedor para satisfacer una necesidad de desarrollo cultural en su comunidad y obtener ingresos económicos por ello, siguiendo las normas de redacción, autenticidad, los criterios establecidos en el área respecto a sus componentes y haciendo énfasis en su viabilidad.',
        "rae": [
            'Identifica los rasgos de la personalidad, y su proyección como estudiante de la modalidad en Artes tomando en cuenta las normas del actuar en esta modalidad.',
            'Argumenta el papel de la cultura y el arte en su sociedad y en el mundo.',
            'Comunica sus ideas y sentimientos, haciendo un uso efectivo de las técnicas, tecnologías y medios de comunicación de la actualidad.',
            'Analiza las fortalezas de su personalidad y de su expresividad, en favor de la proyección de una coherente imagen de sí mismo y de los logros de un plan personal.',
            'Realiza una presentación audiovisual con estrategias aplicadas a la Web 2.0 donde el estudiante se exprese a sí mismo, sus sueños, fortalezas y retos en el marco del aprendizaje de las artes y de su vida.',
            'Argumenta las características del emprendedor cultural.',
            'Identifica las áreas de industrias culturales en República Dominicana y las oportunidades de establecer una empresa cultural.',
            'Elabora la planificación preliminar de un proyecto cultural sencillo, en base a unas determinadas normas de redacción, siguiendo los criterios establecidos en el área respecto a sus componentes y haciendo énfasis en su viabilidad.',
            'Aplica la hoja de cálculo Excel para calcular el presupuesto del proyecto. Contenidos:',
        ],
        "conceptuales": [
        ],
        "procedimentales": [
            'Utilizar correctamente el español de forma verbal y escrita según la situación de comunicación.',
            'Utilizar recursos expresivos corporales y audiovisuales para la comunicación.',
            'Emplear las redes sociales para comunicar la identidad, el arte y la cultura.',
            'Realizar análisis simples estilo FODA.',
            'Planear proyectos productivos preliminares.',
        ],
        "actitudinales": [
            'Valoración de los rasgos personales.',
            'Autenticidad.',
            'Respeto a la diversidad.',
            'Actitud Emprendedora y responsable. Actividades y estrategias de aprendizaje sugeridas: 1. Exposición oral y audiovisual: en los diversos temas comprendidos en los contenidos presentar grabaciones en audio y video que ejemplifiquen. 2. Método de preguntas: en los diversos temas comprendidos en los contenidos. 3. Simulación y juego: en la notación musical utilizar los recursos de Internet, software educativo y otras herramientas virtuales. 4. Aprendizaje basado en problemas: el para cálculos sencillos de presupuesto. 5. Juego de roles. 6. Panel de Discusión: recopilación y análisis comparativo de textos, discografía, audiovisuales e información relativa a las industrias culturales haciendo uso de Internet. 7. Mapas conceptuales: Se recomienda para elementos básicos del lenguaje musical y representación del lenguaje musical. 8. Delineación de la percepción, en el tema de percepción musical. 9. Técnicas de producción creativa: utilizar diversas técnicas para la expresión musical. 10. Asistencia a conciertos y presentación de reportes que recopilen información que los alumnos obtengan de la música escuchada. 11. Técnicas de producción creativa: utilizar diversas técnicas para propuesta del proyecto como lluvia de ideas y sus equivalentes. 12. Método de proyectos: en la elaboración de la propuesta preliminar del proyecto y en el proyecto integrador. Incorporación del Excel. 13. Otro: visitas a industrias culturales dominicanas. Evaluación: RAE Criterios de evaluación Técnicas e instrumentos Resultados del Aprendizaje de evaluación Esperados 1. Identifica los rasgos de la personalidad, y su proyección como estudiante de la modalidad en Artes tomando x Identificación x Informe escrito en cuenta las normas del actuar personal en el sobre sus en esta modalidad. contexto de la proyecciones clase, expresando personales en el su interés futuro. arte. 2. Argumenta el papel de la cultura y el arte en su sociedad y en el mundo. x Claridad en los x Exposición oral en argumentos, panel, sobre papel precisando los del arte y la 3. Comunica sus ideas y aportes. cultura. sentimientos, haciendo un uso efectivo de las técnicas, tecnologías y medios de x Presentación comunicación de la actualidad. visual, con el uso',
            'La síntesis, un buen de tecnología uso de la (power point, o 4. Analiza las fortalezas de su tecnología y la comics. personalidad y de su creatividad. expresividad, en favor de la proyección de una coherente x Realización de',
            'La ética en el arte y imagen de sí mismo y de los análisis Foda, la ética en la logros de un plan personal. 5. Realiza una presentación personal bajo el precisando audiovisual con estrategias compromiso de fortaleza y aplicadas a la Web 2.0 donde el comunicar. debilidades y los estudiante se exprese a sí desafíos que tiene mismo, sus sueños, fortalezas y que afrontar en la retos en el marco del continuidad de sus aprendizaje de las artes y de su estudios de Artes. vida. x Partición en guión de video-grupal.',
            'Realización de 6. Distingue Comportamiento acróstico con los ético personal en las disciplinas valores éticos artísticas. identificados. 7. Argumenta las características x Identifica las x Prueba objetiva del emprendedor cultural. características del con preguntas de emprendedor cultural. selección y',
            'Explica las ensayos cortos características 8. Identifica las áreas de industrias x Identifica las industrias x Informe escrito culturales en República culturales de RD sobre industrias Dominicana y las oportunidades precisando las de su culturales de establecer una empresa localidad. dominicanas y cultural. x Argumenta a partir de posibilidad de las oportunidades y implementación fortalezas, la posibilidad de establecer una industria cultural en su localidad. 9. Elabora la planificación x Determina el producto x Documento escrito preliminar de un proyecto artístico a ofrecer, con de un proyecto cultural sencillo, en base a unas sus correspondientes preliminar cultural. determinadas normas de características, y redacción, siguiendo los justifica su importancia criterios establecidos en el área y oportunidad. respecto a sus componentes y x Describe las haciendo énfasis en su actividades, su viabilidad. cronograma y los roles y funciones de cada involucrado.',
            'Organiza y valora los recursos necesarios en cada una de las etapas/actividades, desagregados en rubros ( tipos de gastos ) 10. Aplica la hoja de cálculo Excel x Utiliza herramientas de x Cálculo del para calcular el presupuesto del formato de celda presupuesto del proyecto. correctamente en una proyecto. hoja de cálculo.',
            'Construye y edita fórmulas con el uso de celdas absolutas y/o relativas.',
            'Construye y edita funciones básicas como suma, promedio, entre otras.',
            'Investiga otras funciones y ejemplifica de acuerdo a las necesidades. Recursos didácticos',
            'Proyector, computadora, internet, cartulina, hojas, Crayones, lápices de colores.',
            'Uso de recursos multimedia para mostrar las industrias culturales en RD y en el mundo.',
            'Uso de Internet para indagación sobre el proyecto preliminar cultural',
        ],
        "indicadores": [
            'El concepto arte y su evolución a documento histórico. través del tiempo x Diferencia los conceptos de Arte,',
            'Glosario de términos (Arte, estética Cultura y Sociedad. y cultura. Las Bellas Artes, entre x Elabora glosario con términos importantes de la estética y la historia otros) del arte.',
            'De la Prehistoria al Arte Medieval x Describe de forma básica las ideas Occidental: su manifestación en la fundamentales del pensamiento cultura dominicana. estético y concepción de belleza, lo',
            'Las maravillas del mundo antiguo, sublime, la fealdad, y la historia del moderno y dominicano. gusto a través del tiempo.',
            'Argumenta los elementos estéticos Arte dominicano desde los principales de los distintos tipos de tiempos precolombino y artes comprendido desde el Arte colonial. Antiguo al Arte Medieval Occidental.',
            'Del Arte Renacentista hasta x Identifica los movimientos artísticos barroco: su manifestación en la comprendidos desde el cultura dominicana. prerrenacentismo al arte pop y explica',
            'Del Arte Neoclásico hasta las las causas del nacimiento de cada estilo artístico. vanguardias siglo XX: su',
            'Argumenta los elementos estéticos manifestación en la cultura. principales de los movimientos y estilos dominicana. artísticos, identificando las obras más',
            'Principios de percepción. representativas del arte universal y',
            'Emoción e imaginación. dominicano.',
            'Elementos que componen el arte. x Elabora un proyecto de apreciación estética de obras de artes dominicanas',
            'Estética y su función. incluyebdo aspectos de la estética',
            'Sensibilidad artística. digital. Procedimentales:',
            'Desarrollar una apreciación estética práctica sobre distintas obras de arte sustentado en los rasgos que cualifican los movimientos y estilos y su relación con el contexto, importancia histórica y repercusiones en el país.',
            'Expresa las distintas manifestaciones artísticas para diversificar su gusto y su consumo artístico.',
        ],
    },
    'Lenguaje Danzario y Teatral': {
        "modulo": 'Formación Artístico-Cultural',
        "horas": '2',
        "introduccion": 'El contacto y desarrollo de las artes escénicas a través de la danza y el teatro ha constituido una práctica cultural transcendente en las grandes civilizaciones, cuya herencia se ha transmitido a través de la representación dramática y obras coreográficas que reflejan en tiempo y espacio los conflictos de personajes emblemáticos, reales o mitológicos de la literatura teatral de grandes épocas de la humanidad. En este sentido, esta asignatura pretende posibilitar la introducción del estudiante al mundo de la danza y el teatro a través de una experiencia reflexiva, lúdica que facilite el desarrollo de competencias.',
        "elemento_competencia": 'Realiza la expresión artística a través de la danza y del teatro, de rasgos de su identidad de modo personal y colectivo, haciendo uso de elementos básicos del lenguaje de las artes escénicas, dando respuesta a los requerimientos escénicos y comunicativos predefinidos para el nivel medio de formación artística.',
        "rae": [
            'Argumenta el rol del lenguaje danzario y teatral en el devenir del desarrollo cultural de la humanidad.',
            'Identifica los principales elementos presentes en el lenguaje corporal como: las expresiones mímicas, el gesto, la postura, la actitud física y las señales que se emiten con el cuerpo en la danza.',
            'Analiza y valorar los diferentes tipos de percepción del movimiento corporal: percepción corporal y sensorial, percepción espacial y audiokinética.',
            'Interpreta o crea fragmentos sencillos de obras escénicas que incorporen la actuación y la danza haciendo uso de los elementos básicos de las técnicas teatral y danzaría. Contenidos:',
        ],
        "conceptuales": [
        ],
        "procedimentales": [
            'Enumera la función social del teatro y la danza en las distintas épocas.',
            'Compara los contenidos y formas de diferentes géneros de la danza.',
            'Describe las características de los principales géneros dramáticos: comedia, tragedia, drama.',
            'Diferencia los géneros teatrales y danzario de forma concisa.',
            'Expresa de forma oral o escrita la idea básica de las técnicas de interpretación dramática y coreográfica.',
            'Reconstrucción de cualidades de la percepción del movimiento corporal.',
            'Interpretación o crea',
            'de fragmentos cortos de danzas, folclóricas o contemporáneas, comunicando rasgos de su identidad.',
            'Experimenta diversas formas de la representación dramática, improvisación, juego dramático.',
        ],
        "actitudinales": [
            'Valora la función social del teatro.',
            'Respeta las diferentes estéticas de las formas teatrales y danzaría.',
            'Valora el uso del cuerpo y la voz como herramientas de expresión.',
            'Valora el cuerpo como instrumento del bailarín.',
            'Interés en la interpretación y concentración en el movimiento propio.',
            'Comunica adecuadamente las ideas y el carácter de los personajes.',
            'Participación cumpliendo con las indicaciones de la danza.',
            'Aprecia el movimiento corporal a través del ritmo o la música. Actividades y estrategias de aprendizaje sugeridas:',
            'Exposición oral y audiovisual: A partir de utilización de sonido e imágenes y expresión oral de los textos.',
            'Método de proyectos: En el proyecto que integra las asignaturas, involucran la interpretación de personajes.',
            'Método de preguntas: En los diversos temas comprendidos en los contenidos.',
            'Simulación y juego: Simular a través de un diseño maque o planos del escenario, diseño de vestuario.',
            'Aprendizaje basado en problemas.',
            'Juego de roles: A partir de improvisación de personajes con distintos roles.',
            'Panel de Discusión: Recopilación y análisis comparativo.',
        ],
        "indicadores": [
        ],
    },
    'Lenguaje Musical': {
        "modulo": 'Formación Artístico-Cultural',
        "horas": '2',
        "introduccion": 'La asignatura Lenguaje Musical integra el desempeño del estudiante en las competencias de reconocer, leer y entender el significado del lenguaje y grafía de la música, en forma auditiva, escrita y reproductiva, así como de los vocablos y sus conceptos propios, mediante la lectura, el análisis auditivo y escrito de fragmentos musicales sencillos. Esta asignatura es importante para todos los alumnos de Bachillerato ya que es un complemento que cohesiona la interrelación de las diferentes manifestaciones artísticas. Competencia: Reproduce audio-visualmente los términos, signos y demás componentes del lenguaje musical relacionados con las cualidades del sonido ayudando al desarrollo del oído musical para complementar el estudio integral de otros perfiles artísticos.',
        "elemento_competencia": 'Realiza la expresión artística a través de la danza y del teatro, de rasgos de su identidad de modo personal y colectivo, haciendo uso de elementos básicos del lenguaje de las artes escénicas, dando respuesta a los requerimientos escénicos y comunicativos predefinidos para el nivel medio de formación artística. Competencias fundamentales: 9 Competencia Ética y Ciudadana. 9 Competencia Comunicativa. 9 Competencia Pensamiento Lógico, Creativo y Crítico. 9 Competencia Resolución de Problemas. 9 Competencia Científico–Tecnológica. 9 Competencia Ambiental y de la Salud. 9 Competencia de Desarrollo ',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
            'Reconoce audio visualmente los signos y términos de la música.',
            'Lee entonadamente un fragmento musical. Entona y reconoce auditivamente, Escalas e Intervalos.',
            'Ejecuta ritmos y polirritmias.',
            'Reconoce auditivamente ejercicios rítmicos y melódicos utilizando compases Binarios y ternarios.',
        ],
        "actitudinales": [
        ],
        "indicadores": [
        ],
    },
    'Lenguaje Visual, Dibujo y Creación de Personajes': {
        "modulo": '',
        "horas": '5',
        "introduccion": 'La expresión artística a través de las artes visuales y las artesanías invita al juego creativo usando los colores, las texturas, las formas, a la creación de imágenes u objetos utilitarios o de fines decorativos a través de diferentes medios convencionales o digitales, así como de reconocer el rol e importancia de estas en la época actual enfatizándose en la identidad cultural. El proceso de diseño de personaje trata de desarrollar los conceptos o ideas que van surgiendo a lo largo del proceso, hasta dar con la imagen más adecuada para el personaje, que podrá ser utilizada posteriormente en ilustraciones, cómics, animación, videojuegos, etc. El interés de este trabajo ha residido en el deseo de abordar esta forma de ilustración, que es el concept art. De esta manera, Los contenidos expresados en esta asignatura ayudaran al estudiante a la correcta conceptualización, descripción y desarrollo del personaje. Atravez de esta asignatura se desarrollará la ficha de personaje, este es un documento con apartados pautados que nos ayudará a definir todos aquellos aspectos que forman un personaje y a construirlo en su conjunto. La misma, abarca todo el desarrollo visual: los bocetos, que se ',
        "elemento_competencia": 'Comunica a través del lenguaje visual y del personaje creado, las características de la personalidad conceptualizada, el estilo de vida y su relación con el medio circundante utilizando medios tradicionales y digitales de dibujo, aplicación de textura, color, profundidad, etc.',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
            'Identificar las diversas modalidades de las artes visuales y las artesanías y su evolución histórica.',
            'Percibir visualmente elementos del lenguaje visual.',
            'Realizar el diseño de una imagen visual aplicando técnicas elementales.',
            'Experimenta con técnicas y materiales artesanales.',
            'Elabora obras artísticas visuales y artesanales haciendo uso de los elementos básicos y técnicas. Preparar una descripción conceptual de la personalidad del objeto escogido.',
            'Jugar con el objeto, recreando su personalidad, voz y movimiento.',
            'Estudiar, que es la personalidad, cuales son las características de los arquetipos de Jung para el desarrollo de los personajes.',
            'Preparar conceptualmente las actitudes y personalidad de un personaje ficticio usando las fichas de descripción con el siguiente formulario:',
            'Nombre:',
            'Edad y lugar de nacimiento:',
            'Relación con la infancia: ¿cómo fue su infancia? ¿Cómo ha influenciado en su vida? ¿Qué relación tenía con familiares, amigos, padres…?',
            'Relación con la adolescencia: ¿Qué relación tuvo con el despertar de su sexualidad? ¿Y con su cuerpo? ¿Vivió el paso a la vida adulta de una manera saludable? ¿Optó por una actitud rebelde? ¿Represora?',
            'Relación con su familia: ¿Se lleva bien? ¿Se siente aceptado/a?',
            'Relación con los espacios: ¿Qué relación tiene con el lugar en el que vive actualmente? ¿Cuál es su lugar soñado? ¿Ha encontrado su espacio en la vida? ¿Su lugar de nacimiento afecta a su vida?',
            'Relación con su cuerpo: ¿Se siente atractivo/a? ¿Tiene complejos corporales? ¿Se cuida y es deportista? ¿No le interesa para nada su físico? ¿Cómo viste? ¿Usa la vestimenta para lucir, aparentar? ¿Ni piensa en esas cosas…? ¿Fuma? ¿Se droga?',
        ],
        "actitudinales": [
            'Responsabilidad y disciplina.',
            'Valorar los aportes de las artes visuales y las artesanías en la época actual.',
            'Estudiar los objetos físicos a su alrededor para poder describirlos.',
            'Interés por la observación y orden.',
            'Interés por la descripción y la introspección.',
            'Desarrollo de habilidades creativas.',
            'Prudencia, respeto por los procesos de creación. Actividades y estrategias de aprendizaje sugeridas:',
            'Exposición oral y audiovisual: en los diversos temas comprendidos en los contenidos presentar exposiciones y video que ejemplifiquen los conceptos impartidos en el aula.',
            'Método de proyecto: Proyecto de creación de personaje, con todos los elementos, pautas y procesos que conlleva hasta su fase final.',
            'Método de preguntas: que afiancen el aprendizaje respecto a los conceptos, características, identificación, clasificación, pautas para el desarrollo de todos los aspectos que componen un personaje.',
            'Aprendizaje basado en problemas: Diseña los personajes de manera tradicional y digital (para animación, comic o cuento) partiendo de las fichas creadas. Todos los dibujos que se han realizado con lápiz y posteriormente digitalizados, el color, textura se añadirán en Photoshop y los detalles realzados con la tableta gráfica.',
            'Juego de roles: el estudiante explica a sus compañeros el método aprendido y sus diversas etapas.',
            'Panel de Discusión: al finalizar una jornada se discute sobre los avances de los proyectos de desarrollo de personajes.',
            'Técnicas de producción creativa: 1. Lluvia de ideas: técnicas utilizadas de forma grupal para generar o producir ideas. 2. Análisis morfológico: es útil para descomponer un problema en sus elementos más básicos, creando una matriz que facilita la combinación aleatoria de las distintas posibilidades existentes en cada uno de ellos. 3. Empatía: facilita la percepción desde una perspectiva ajena al individuo.',
            'Visita: Visitas a museos, galerías de arte de forma presencial o haciendo uso de entornos virtuales. Evaluación: Resultados del Aprendizaje 1. Criterios de evaluación Técnicas e instrumentos Esperados de evaluación 1. Argumenta el rol del x Argumenta acerca de la x Análisis de video lenguaje visual y artesanal importancia de las introductorio de artes visuales a través y su evolución atreves de de un análisis y una las artes visuales y la historia. prueba escrita. las artesanías.',
        ],
        "indicadores": [
        ],
    },
    'Medios de Comunicación': {
        "modulo": '',
        "horas": '',
        "introduccion": 'Medios de Comunicación es una asignatura que permite al estudiante conocer la historia y evolución de los medios de comunicación a nivel mundial y en la República Dominicana; así como la importancia e influencia de los mismos en la sociedad en que vivimos. Con esta materia el estudiante desarrolla habilidades de gestión y comunicación para interactuar en grandes equipos interdisciplinarios y en el plano de las estructuras organizacionales, en los eventos, programación y difusión. El objetivo de esta asignatura es crear en el alumno el pensamiento crítico, analítico, social y creativo, al tiempo de comprender el funcionamiento de los medios de comunicación, teniendo en consideración las funciones de informar, educar, orientar y entretener de los mismos. En tal sentido, se abordan temas como los medios de comunicación de difusión masiva, los tipos y las funciones de los medios de comunicación, y la influencia de los mismos en la sociedad. Por lo que al final de la asignatura el alumno podrá evaluar y analizar los contenidos emitidos dentro de la programación de los distintos medios de comunicación, las relaciones comerciales y de negocios, así como analizar los ratings de las distint',
        "elemento_competencia": 'Apreciación del Diseño y la Comunicación Multimediática (ADCM 2.1) Elemento de Competencia: Desarrolla habilidades de gestión en el manejo de las redes sociales, utilizando las mismas como herramienta de comunicación.',
        "rae": [
        ],
        "conceptuales": [
            'Planificación de clases. x Planifica contenidos a ser compartidos',
            'Manejo y uso de las herramientas a a través de las redes sociales. utilizar por el estudiantado.',
            'Método de enseñanza según nivel de x Utiliza la plataforma de las redes conocimiento del estudiantado. sociales para comunicarse de manera efectiva.',
            'Evaluación del aprendizaje individual y x Utiliza las redes sociales como colectivo del alumno. herramienta de comunicación para',
            'Manejo adecuado de terminología. alcanzar públicos y clientes potenciales de largo alcance.',
        ],
        "procedimentales": [
        ],
        "actitudinales": [
            'Fomenta actitud ética, responsable y emprendedora.',
            'Fomenta actitud crítica.',
            'Fomenta actitud sociable.',
            'Fomenta la creatividad.',
            'Fomenta el pensamiento analítico.',
            'Valora el proceso de enseñanza- aprendizaje.',
            'Desarrolla el sentido de organización y desarrollo.',
            'Fomenta la comunicación. Rango de Aplicación:',
        ],
        "indicadores": [
        ],
    },
    'Operación de Cámara de Video': {
        "modulo": 'Formación Para diseño y creatividad multimedia (DCM. 2)',
        "horas": '4',
        "introduccion": 'Videocámara es una asignatura por competencia, que da continuidad a la fotografía I y fotografía II. Demanda asimilación de conocimientos y desarrolla de habilidades y actitudes. El proceso de enseñanza – aprendizaje permitirá el dominio del conocimiento tanto teórico como practico de la asignatura. En esta unidad de aprendizaje el estudiante aprende sobre la evolución de los medios visuales digital, el manejo de la cámara de video y la edición de video y sus usos adecuados. Analiza la relación del video con el arte y su función como medio de comunicación y expresión artística. Competencia: Aplica técnicas y principios de video, en proyectos de expresión artísticos y como medio de comunicación Resultados de aprendizaje esperados: 1. Explica los orígenes de la televisión, y los primeros intentos para transmitir imagen y audio a distancia. Y la televisión como medio de comunicación de masas. 2. Identificará, los formatos de transmisión más utilizados, sus dimensiones y regiones. 3. Identifica de manera oral los aspectos más significativos del origen y surgimiento del cine; las características y elementos que aportaron de manera significativa a su desarrollo. 4. Identifica de manera o',
        "elemento_competencia": 'Animación Artística 2.1 (AA2.1) Elemento de competencia: Construye un guion que funciona de soporte o base para las produciones audiovisuales tomando en cuenta los fundamentos y elementos que componen el guión literario y técnico',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
            'Distingue una buena idea',
            'Crea historias',
            'Describe personajes principales y secundarios',
            'Hace el guion técnico correspondiente a esa historia.',
        ],
        "actitudinales": [
            'Identidad',
            'Creatividad',
        ],
        "indicadores": [
        ],
    },
    'Producción Audiovisual': {
        "modulo": 'Formación para diseño y creatividad multimedia (DCM.3)',
        "horas": '4',
        "introduccion": 'La asignatura tiene como objeto dotar al estudiante de los conocimientos y técnicas de la producción audiovisual, que los guíen desde la fase de planificación hasta la fase de producción del proyecto audiovisual de alto contenido informativo y estético.',
        "elemento_competencia": 'Integra los conceptos básicos de la planificación de proyectos audiovisuales, con el fin diseñar y producir material y proyectos audiovisuales para ser colocado en diferentes soportes digitales que cumplan con necesidades estéticas y artísticas. Resultados de aprendizaje esperados: 1 Identifica los equipos necesarios dependiendo de la necesidad a la hora de producir material audiovisual. 2 Graba audio y sonido de manera eficiente. 3 Identifica y clasifica lo timbres de voces. 4 Reconoce y realiza las etapas de producción audiovisual. 5 Crea productos audiovisuales de calidad. 6 Realiza de mane',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
        ],
        "actitudinales": [
            'Fomento de la actitud responsable.',
            'Fomento de la creatividad.',
            'Desarrollo de la comunicación por medio del audio y video.',
            'Fomento de la planificación.',
            'Fomento del trabajo en equipo.',
        ],
        "indicadores": [
            'Planos de la cámara. x Utiliza de forma correcta los',
            'Transiciones visuales. planos de las cámaras.',
            'Iluminación x Conoce los tipos de transiciones,',
            'Dirección de arte dependiendo de la situación.',
            'Libro de producción x Aplica los términos técnicos de la producción audiovisual.',
        ],
    },
    'Redes Sociales': {
        "modulo": '',
        "horas": '4',
        "introduccion": 'Las redes sociales son estructuras sociales compuestas por grupos de personas que están conectadas por uno o varios tipos de relaciones (amistad, parentesco, intereses comunes, etcétera). El objetivo fundamental de las mismas lo constituye el facilitar la comunicación, interacción y cooperación entre los miembros de una sociedad. Desde el ámbito de la intimidad para auto revelarnos hasta el ámbito laboral, el mundo de los negocios, en la cultura, la política, la economía, etc. Con esta materia se busca educar al estudiante en lo referente a las redes sociales, su importancia y utilidad, al tiempo de enseñarles a los alumnos el manejo adecuado de las principales plataformas virtuales de comunicación utilizadas a nivel personal y profesional. Plataformas virtuales como: Facebook, Twitter, Google Plus, YouTube, Pinterest, WhatsApp, LinkedIn, Skype, Instagram, Snapchat, etc.',
        "elemento_competencia": 'Diseño y Creatividad Multimedia 3.1 (DCM 3.1) 14. 13. Elemento de competencia Integra los conceptos básicos de la planificación de proyectos audiovisuales, con el fin diseñar y producir material y proyectos audiovisuales para ser colocado en diferentes soportes digitales que cumplan con necesidades estéticas y artísticas.',
        "rae": [
        ],
        "conceptuales": [
        ],
        "procedimentales": [
        ],
        "actitudinales": [
            'Fomento de la actitud responsable.',
            'Desarrollo de la comunicación por medio del audio y video.',
            'Fomento de la planificación.',
            'Fomento de la creatividad.',
            'Fomento del trabajo en equipo.',
        ],
        "indicadores": [
            'Inventos relevantes para la x Identifica los equipos necesarios comunicación. dependiendo de la necesidad a la hora',
            'Puntos fundamentales de la de producir material audiovisual. producción audiovisual; Audio y x Graba audio y sonido de manera video. eficiente.',
            'El guion. x Identifica y clasifica lo timbres de',
            'Locución y timbre de voces. voces.',
            'Reacciones y sentimientos en el x Crea productos audiovisuales de material audiovisual. calidad.',
            'Planos de la cámara. x Reconoce y realiza las etapas de',
            'Transiciones visuales. producción audiovisual.',
            'Iluminación x Realiza de manera eficiente el guion',
            'Dirección de arte para producción.',
            'Libro de producción x Indicadores de logros',
            'Utiliza de forma correcta los planos de',
        ],
    },
    'Videoarte': {
        "modulo": 'Formación Para diseño y creatividad multimedia (DCM.3)',
        "horas": '5',
        "introduccion": 'En la asignatura Videoarte el estudiante experimenta y profundiza posibilidades narrativas con intención artística, comunicativa o informativa. La creación audiovisual se consigue mediante recursos técnicos, estéticos y conceptuales. Con esta asignatura se fomenta la creatividad, el análisis crítico, síntesis de ideas, apreciación estética y el trabajo en equipo.',
        "elemento_competencia": 'Animación Artística (AA. 3.1) Elemento de competencia: Anima, dibujos, objetos y personajes de manera tradicional y digital 2D y 3D, comprendiendo el tiempo y espacio, a través, del uso de los key frames, las principales herramientas de After Effects y la edición de videos en Premiere, creando el rigging, aplicando el blend shapes, y añadiendo movilidad en los gestos y todo el cuerpo en Maya o 3Dmax. Competencia Fundamentales: 9 Competencia Ética y Ciudadana. 9 Competencia Comunicativa. 9 Competencia Pensamiento Lógico, Creativo y Crítico. 9 Competencia Resolución de Problemas. 9 Competencia C',
        "rae": [
        ],
        "conceptuales": [
            'Planifica el movimiento de',
            'Animación característica y manera tradicional. manifestaciones.',
            'Crea la estructura interna con sus',
            'Historia y evolución de la articulaciones del personaje para animación. stop motion.',
            'El rol del animador en un estudio de',
            'Desarrolla el exterior y detalles animación. del personaje para stop motion.',
            'Pensamientos lógicos y',
            'Juga con el objeto, recreando su descriptivos. personalidad, voz y movimiento.',
            'Arte conceptual y su relación con la',
            'Prepara conceptualmente las animación. actitudes y personalidad del',
            'El comic y las ilustraciones. personaje.',
            'La dinámica y acción del objeto.',
            'El dibujo animado x Usa la cámara fotográfica y el',
            'La anatomía, equilibrios y Dragon frame en la captura composición. fotográfica para el stop motion.',
            'La luz, la sombra, la textura, el x Realiza el Planteamiento del fondo y el color. personaje dibujado frontalmente,',
        ],
        "procedimentales": [
        ],
        "actitudinales": [
            'inclinación por la observación y orden.',
            'Interés por la descripción.',
            'Desarrollo de habilidades creativas.',
            'Prudencia, respeto por los procesos de creación.',
            'Aptitud positiva por la animación y todos sus procesos.',
            'Interés por el espacio 2D y 3D, creación del movimiento.',
            'Interés por los efectos visuales.',
        ],
        "indicadores": [
            'Explica la historia y evolución de la animación.',
        ],
    },
}

# Alias para nombres alternativos de asignaturas
ALIAS_ASIGNATURAS = {
    'Fotografia': 'Fotografía',
    'FOTOGRAFIA': 'Fotografía',
    'Diseno Web': 'Diseño Web',
    'DISEÑO WEB': 'Diseño Web',
    'Diseno Basico y Expresion Visual': 'Diseño Básico y Expresión Visual',
    'Guión': 'Guion',
    'GUION': 'Guion',
    'Identidad, Cultura y Comunicación': 'Identidad, Cultura y Emprendimiento',
    'Introducción a la Historia del Arte universal y Dominicano': 'Historia del Arte Universal y la Estética Digital',
    'Historia del Arte': 'Historia del Arte Universal y la Estética Digital',
}


def get_asignatura(nombre: str) -> dict:
    """
    Obtiene los datos oficiales de una asignatura por nombre.
    Devuelve un dict vacío si no se encuentra (nunca None, para simplificar uso).
    Busca con alias y match fuzzy por substring.
    """
    if not nombre:
        return {}
    nombre = nombre.strip()
    # Match exacto
    if nombre in CURRICULUM_MULTIMEDIA:
        return CURRICULUM_MULTIMEDIA[nombre]
    # Alias
    canon = ALIAS_ASIGNATURAS.get(nombre)
    if canon and canon in CURRICULUM_MULTIMEDIA:
        return CURRICULUM_MULTIMEDIA[canon]
    # Case-insensitive
    nlow = nombre.lower()
    for k in CURRICULUM_MULTIMEDIA:
        if k.lower() == nlow:
            return CURRICULUM_MULTIMEDIA[k]
    # Substring match
    for k in CURRICULUM_MULTIMEDIA:
        if nlow in k.lower() or k.lower() in nlow:
            return CURRICULUM_MULTIMEDIA[k]
    return {}


def formatear_contexto_curriculo(nombre: str) -> str:
    """
    Formatea el currículo oficial de una asignatura como texto plano
    para inyectar en el prompt del sistema de IA.
    """
    d = get_asignatura(nombre)
    if not d:
        return ""
    partes = []
    if d.get("modulo"):
        partes.append(f"MÓDULO: {d['modulo']}")
    if d.get("horas"):
        partes.append(f"HORAS SEMANALES: {d['horas']}")
    if d.get("introduccion"):
        partes.append(f"INTRODUCCIÓN OFICIAL:\n{d['introduccion']}")
    if d.get("elemento_competencia"):
        partes.append(f"ELEMENTO DE COMPETENCIA OFICIAL:\n{d['elemento_competencia']}")
    if d.get("rae"):
        raes = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(d["rae"][:8]))
        partes.append(f"RESULTADOS DE APRENDIZAJE ESPERADOS (RAE):\n{raes}")
    if d.get("conceptuales"):
        items = "\n".join(f"  - {c}" for c in d["conceptuales"][:10])
        partes.append(f"SABERES CONCEPTUALES:\n{items}")
    if d.get("procedimentales"):
        items = "\n".join(f"  - {p}" for p in d["procedimentales"][:10])
        partes.append(f"SABERES PROCEDIMENTALES:\n{items}")
    if d.get("actitudinales"):
        items = "\n".join(f"  - {a}" for a in d["actitudinales"][:8])
        partes.append(f"SABERES ACTITUDINALES:\n{items}")
    if d.get("indicadores"):
        items = "\n".join(f"  - {i}" for i in d["indicadores"][:8])
        partes.append(f"INDICADORES DE LOGRO:\n{items}")
    return "\n\n".join(partes)
