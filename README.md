# ReliefGrid

Espacio de coordinación de emergencias, diseñado para reducir al mínimo la
fricción al compartir el triaje, la disponibilidad y el despliegue de equipos de
respuesta, y el registro de actividad.

Producción: `https://davefrassoni.com/emergency/`

## Por qué se llama ReliefGrid

**Relief** comunica ayuda humanitaria, socorro y recuperación sin limitar el
producto a un solo tipo de desastre. **Grid** representa tanto la cuadrícula
geográfica del mapa como la red de personas, equipos, incidentes y suministros
que deben coordinarse. Juntas, las dos palabras describen la idea central del
producto: una vista compartida donde toda la respuesta puede ubicarse,
conectarse y actuar.

El nombre es corto, internacional, fácil de pronunciar en varios idiomas y
permite que el producto crezca más allá de terremotos hacia inundaciones,
incendios, desplazamientos u otras crisis.

## Funcionalidades

- Cualquier persona puede abrir una operación privada de respuesta sin crear
  previamente una cuenta. Todas las operaciones son privadas de forma
  predeterminada.
- Los administradores pueden publicar la operación para que cualquier persona
  con el enlace consulte el mapa seguro. Las operaciones públicas aparecen en
  la página principal.
- De forma independiente, los administradores pueden permitir reportes públicos
  geolocalizados y no verificados, sin exponer datos de equipos ni de
  informantes.
- Los usuarios públicos pueden publicar necesidades detalladas de suministros,
  con cantidades y unidades. Otras personas pueden comprometerse a cubrir una
  parte o la totalidad de lo pendiente, sin exceder la cantidad solicitada.
- Cualquier persona puede reportar a alguien desaparecido en el último punto
  donde fue visto. El público puede consultar los datos útiles para la búsqueda,
  mientras el contacto del informante permanece privado. Los coordinadores
  pueden verificar el reporte, priorizarlo y asignar equipos de búsqueda y
  rescate.
- Las operaciones tienen nombres de código únicos, por lo que el mapa público
  puede utilizar una ruta fácil de recordar, como `/venezuela`.
- El correo del administrador es obligatorio. Un administrador que regresa
  puede solicitar un enlace de acceso por correo, válido durante 20 minutos,
  para autorizar un dispositivo nuevo sin invalidar los dispositivos existentes.
- La interfaz detecta el idioma del navegador y admite español, inglés, francés,
  italiano, chino, ruso y hebreo, incluido el diseño de derecha a izquierda.
- El formulario integrado para solicitar funcionalidades valida el correo de
  contacto, almacena la solicitud y la envía a `FEATURE_REQUEST_EMAIL`.
- Quienes aportan suministros reciben un enlace privado para actualizar el
  estado, la hora estimada de llegada, el origen, las notas y, opcionalmente, la
  ubicación GPS en vivo. La posición precisa solo es pública mientras la persona
  habilita expresamente su difusión.
- Los administradores generan invitaciones de un solo uso, válidas durante
  72 horas, para coordinadores, observadores u otros administradores.
- Los coordinadores registran emergencias con ubicación, prioridad de triaje
  asignada en campo, cantidad de personas afectadas o atrapadas, peligros y
  datos del informante.
- Los equipos publican su capacidad y disponibilidad. Un equipo no puede estar
  desplegado en dos emergencias al mismo tiempo.
- Toda acción relevante queda registrada en la bitácora compartida de la
  operación.
- Los cambios llegan mediante WebSockets. Si el socket está bloqueado o se
  desconecta, el cliente cambia automáticamente a consultas de larga duración
  cada 25 segundos.

Los niveles de acceso están separados deliberadamente:

- **Público:** consulta el mapa público y envía reportes no verificados.
- **Observador:** consulta toda la operación privada.
- **Coordinador:** verifica y clasifica incidentes, gestiona recursos y asigna
  equipos.
- **Administrador:** posee todos los permisos del coordinador y además gestiona
  invitaciones y el acceso público.

Los secretos de acceso e invitación se almacenan como hashes SHA-256. La clave
utilizable de la operación permanece en el almacenamiento local del navegador
del integrante. Toda instalación real debe utilizar HTTPS, ya que los enlaces y
el almacenamiento del navegador funcionan como credenciales al portador.

## Desarrollo local

Requisitos: Python 3.12 o posterior y Node.js 20 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

En una segunda terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:5173`. Si se omiten `DATABASE_URL` y `REDIS_URL`, el
entorno local utiliza SQLite y un canal de eventos en memoria. El servidor de
desarrollo de Django ejecuta la aplicación ASGI para el tráfico HTTP y
WebSocket.

## Despliegue con PostgreSQL

Copiar `.env.example` como `.env`, reemplazar los secretos de Django y
PostgreSQL, y configurar `FRONTEND_URL` y `ALLOWED_HOSTS` con los valores
públicos. Después, ejecutar:

```powershell
docker compose up --build
```

De forma predeterminada, la aplicación queda disponible en
`http://localhost:8080`. Docker Compose ejecuta PostgreSQL, Redis, Django
Channels con Daphne y el frontend Vue servido por Nginx.

El servidor de producción revisa la rama `main` de GitHub cada minuto mediante
las unidades systemd ubicadas en `deploy/`. Cada commit nuevo se descarga por
avance rápido y se despliega con Docker Compose. Si la actualización falla o no
puede aplicarse por avance rápido, la versión que está funcionando permanece
intacta.

## Fuentes externas

El servicio `worker` ejecuta `sync_feeds` periódicamente. Cada registro importado
conserva la URL de origen, el identificador externo, la carga útil saneada, el
hash de contenido y el vínculo con el incidente no verificado generado. Las
actualizaciones son idempotentes y los registros externos aparecen marcados en
la interfaz como `External · verify`.

Después de crear la operación, registrar la fuente descubierta para Venezuela:

```powershell
docker compose exec backend python manage.py seed_venezuela_feed --codename venezuela
```

La fuente está deshabilitada de forma predeterminada porque su API de personas
requiere reCAPTCHA incluso para las consultas de lectura. Solo debe habilitarse
cuando sus responsables proporcionen una fuente legible por máquinas y
autorizada, o una credencial incluida en su lista de acceso. El worker no evade
controles contra automatización.

## Correo en producción

Configurar `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `DEFAULT_FROM_EMAIL` y
`FEATURE_REQUEST_EMAIL` en `.env`. El acceso sin contraseña y las solicitudes
de funcionalidades utilizan el mismo transporte de correo de Django. El backend
de Docker Compose puede comunicarse con un relay SMTP instalado en el servidor
mediante `host.docker.internal`.

## Verificación

```powershell
cd backend
python manage.py test
python manage.py check

cd ..\frontend
npm run build
```

## Límite operativo importante

ReliefGrid registra decisiones tomadas en campo; no es un sistema clínico de
triaje, una herramienta de evaluación estructural, una autoridad de despacho ni
un reemplazo de los protocolos locales de mando de incidentes.

Una instalación de producción debe mantener HTTPS, copias de seguridad
probadas, monitoreo, una estrategia para trabajo sin conexión o con conectividad
limitada y una política de conservación de datos adecuada para las
organizaciones responsables.
