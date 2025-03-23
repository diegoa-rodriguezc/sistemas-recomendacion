# Taller 1: Sistemas de Recomendación

El presente Taller se ha realizado usando las herramientas:
- FastAPI
- Python (3.9)
- Postgres (17)

## Estructura del proyecto

```
.
├── data/
│   ├── df_sample.csv
│   ├── modelItem_pearson.joblib
│   ├── modelUser_pearson.joblib
│   ├── movie.csv
│   ├── MovieLens_Dataset.zip
│   ├── rating.csv
│   ├── test_df.csv
│   └── train_df.csv
├── data/
│   ├── database.py
│   ├── models.py
│   ├── session.py
│   └── tables.py
├── static/
│   └── js/
│       └── app.js
├── templates/
│   ├── index.html
│   └── login.html
├── app.py
└── requeriments.txt

```

## Instalación

### Requerimientos

- **Sistema Operativo**: Windows 10/11, macOS 10.15 o superior, distribuciones de Linux.
- **Python**: Versiones >= 3.9. Se recomienda utilizar un entorno virtual para evitar conflictos de dependencias.
- **Librerías**: utilizar el archivo `requirements.txt` para la instalación de las mismas.

### Configuración e Instalación

> **NOTA** Asegúrese de tener instalado `git` en su máquina o `GitHub Desktop` para la clonación del repositorio.

En una ventana de comandos (cmd/terminal), ejecutar los comandos que a continuación se describen:

**Clonar el repositorio**:

Clone el repositorio en su entorno local:
   ```bash
   git clone https://github.com/diegoa-rodriguezc/sistemas-recomendacion.git
   ```
   Cambie al directorio del proyecto:
   ```bash
   cd Taller1
   ```

### Instalación

> En una ventana de comandos (cmd/terminal) y ubicado en la carpeta `Taller1`.

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

> **NOTA** Antes de iniciar el servidor se deben ajustar los parámetros de conexión al servidor de Base de datos (usuario, contraseña, servidor, puerto y nombre del esquema), para lo cual se debe modificar el archivo denominado `database.py`. 
Los atributos a modificar son `user`, `password`, `host`, `port` y `databasename` .
Usar la cadena de conexión según corresponda para usar MS SQL Server o PostgreSQL.

5. Una vez ajustado los atributos de la Base de Datos, ejecutar la creación de tablas mediante el comando: 
```bash
python -m db.tables
```

6. Posterior a la instalación de dependencias y ajuste del archivo de conexión a Base de Datos, iniciar el servidor para uso del API
uvicorn nombre_del_archivo:app --reload

```bash
uvicorn app:app --reload
```

7. Una vez el servidor presente el mensaje de inicio correcto, similar al siguiente, se puede acceder a la aplación:
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   INFO:     Started reloader process [15952] using StatReload
   INFO:     Started server process [10220]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   ```

8. Una vez se han creado las tablas en la base de datos, se procede a la carga de datos, accediendo mediante un navegador a la URL http://127.0.0.1:8000/docs/ y usando el end-point según corresponda:
- Carga de archivo `data/movie.csv` usar el end-point `/upload/movie`, dar clic en la opción denominada *Try it out* para seleccionar el archivo mencionado
- Carga de archivo `data/rating.csv` usar el end-point `/upload/rating`, dar clic en la opción denominada *Try it out* para seleccionar el archivo mencionado

> **NOTA** La carga de información se puede demorar dada la cantidad de registros a ser insertados en las tablas.

> ⚠️ Si se ejecuta varias veces este paso de carga de información, se pueden perder datos previamente almacenados dado que este hace una limpieza de información antes de insertar la misma.

Se pueden explorar los demás end-point de la URL mencionada


## Acceso a aplicación

> **NOTA** Si es la primera vez que ingresa a la aplicación y NO ha realizado la carga de datos acorde a lo mencionado previamente, el sistema no podrá generar ni visualizar la información correctamente. Si ya se ha cargado las tablas respectivas, omitir este mensaje.
 
Una vez se ha iniciado el servidor, se debe acceder a la url http://127.0.0.1:8000/ 

Una vez cargada la página, se evidencia la interfaz de acceso donde se ingresa mediante la digitación de un `id` de usuario, o crear un nuevo usuario ingresando al botón de `Registrar`.

## Equipo de Trabajo

| Nombre | 
|-------------|
| Andrés Felipe Mendez Antolínez |
| Diego Alberto Rodríguez Cruz |
| Harvy José Benítez Amaya |
| Juan José Ramírez Cala |
