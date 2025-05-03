# Taller 1: Sistemas de Recomendación

El presente Taller se ha realizado usando las herramientas:
- FastAPI
- Python (3.9)
- Postgres (17)

## Estructura del proyecto

```
.
├── app/
│   ├── data/
│   │   └── ** Por temas de espacio no se sube la data dado su tamaño (>5GB) **
│   ├── db/
│   │   ├── database.py
│   │   ├── load_data.py
│   │   ├── loadtables.py
│   │   ├── models.py
│   │   ├── session.py
│   │   └── tables.py
│   ├── model/
│   │   └── hybrid_model.joblib
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── main.js
│   ├── templates/
│   │       ├── about.html
│   │       ├── base.html
│   │       ├── business_details.html
│   │       ├── index.html
│   │       ├── login.html
│   │       ├── recommendations.html
│   │       └── user_profile.html
│   ├── appFastAPI.py
│   ├── recommender_model.py
│   └── requeriments.txt
├── sintonización/
│   ├── Taller2_03_af_mendez_da_rodriguezc123_h_benitez_jj_ramirezc1.ipynb
│   ├── Taller2_03_af_mendez_da_rodriguezc123_h_benitez_jj_ramirezc1.html
│   └── Taller2_03_af_mendez_da_rodriguezc123_h_benitez_jj_ramirezc1_Notebook.pdf
└── README.md

```

## Instalación

### Requerimientos

- **Sistema Operativo**: Windows 10/11, macOS 10.15 o superior, distribuciones de Linux.
- **Python**: Versiones >= 3.9. Se recomienda utilizar un entorno virtual para evitar conflictos de dependencias.
- **Librerías**: utilizar el archivo `requirements.txt` para la instalación de las mismas.

### Configuración e Instalación

> ✎ **NOTA** Asegúrese de tener instalado `git` en su máquina o `GitHub Desktop` para la clonación del repositorio.

En una ventana de comandos (cmd/terminal), ejecutar los comandos que a continuación se describen:

**Clonar el repositorio**:

> ℹ️ Seleccione una ruta en su equipo/máquina donde desea almacenar los archivos del presente proyecto.

Clone el repositorio en su entorno local:
   ```bash
   git clone https://github.com/diegoa-rodriguezc/sistemas-recomendacion.git
   ```
   Cambie al directorio del proyecto:
   ```bash
   cd Taller2/app
   ```

### Instalación

En una ventana de comandos (cmd/terminal) y ubicado en la carpeta `Taller2/app` proceder con los siguiente pasos:

1. Instalar la libería respectiva para crear un entorno virtual de trabajo

```bash 
pip install virtualenv
```

2. Creación de entorno virtual
```bash 
python -m venv env
```

3. Activación de entorno virtual, previamente creado
    * En Windows, ejecutar:
    ```bash
    .\env\Scripts\Activate.ps1
    ```
    * En Linux, ejecutar:
    ```bash
    source env/bin/activate
    ```

4. Posterior a la activación del entorno virtual, se procede a realizar la instalación de dependiencias, con el comando:
```bash
pip install -r requirements.txt
```

para windows
```bash
python -m db.load_data_copy `
   .\data\yelp_academic_dataset_business.json `
   .\data\yelp_academic_dataset_checkin.json `
   .\data\yelp_academic_dataset_review.json `
   .\data\yelp_academic_dataset_tip.json `
   .\data\yelp_academic_dataset_user.json
```

> ✎ **NOTA** Antes de iniciar el servidor se deben ajustar los parámetros de conexión al servidor de Base de datos (usuario, contraseña, servidor, puerto y nombre del esquema), para lo cual se debe modificar el archivo denominado `database.py`.
"postgresql://`USER`:`PASSWORD`@`SERVER`:`PORT`/`SCHEMA`".

> ℹ️ La base de datos utilizada es PostgreSQL, con nombre de esquema `sr_yelp`; se puede usar un nombre de esquema diferente si se prefiere.

5. Una vez ajustado los atributos de la Base de Datos, ejecutar la creación de tablas mediante el comando: 
```bash
python -m db.tables
```


6. Posterior a la instalación de dependencias y ajuste del archivo de conexión a Base de Datos, iniciar el servidor para uso del API
uvicorn nombre_del_archivo:app --reload

```bash
uvicorn appFastAPI:app --reload
```

7. Una vez el servidor presente el mensaje de inicio correcto, similar al siguiente, se puede acceder a la aplación:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   INFO:     Started reloader process [15952] using StatReload
   INFO:     Started server process [10220]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   ```

> ✎ **NOTA** La carga de información se puede demorar dada la cantidad de registros a ser insertados en las tablas.

> ⚠️ Si se ejecuta varias veces este paso de carga de información, se pueden perder datos previamente almacenados dado que este hace una limpieza de información antes de insertar la misma.

Se pueden explorar los demás end-point de la URL mencionada


## Acceso a aplicación

> ✎ **NOTA** Si es la primera vez que ingresa a la aplicación y NO ha realizado la carga de datos acorde a lo mencionado previamente, el sistema no podrá generar ni visualizar la información correctamente. Si ya se ha cargado las tablas respectivas, omitir este mensaje.
 
Una vez se ha iniciado el servidor, se debe acceder a la url http://127.0.0.1:8000/ 

Una vez cargada la página, se evidencia la interfaz de acceso donde se ingresa mediante la digitación de un `user_id` de usuario, o seleccione uno de la lista para la prueba.

## Equipo de Trabajo

| Nombre | 
|-------------|
| Andrés Felipe Mendez Antolínez |
| Diego Alberto Rodríguez Cruz |
| Harvy José Benítez Amaya |
| Juan José Ramírez Cala |
