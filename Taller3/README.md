# Taller 3: Sistema de Recomendación de Películas

El presente Taller se ha realizado usando las herramientas:
- FastAPI
- Python (3.9)
- React
- NodeJS

## Instalación

### Requerimientos

- **Sistema Operativo**: Windows 10/11, macOS 10.15 o superior, distribuciones de Linux.
- **Python**: Versiones >= 3.9. Se recomienda utilizar un entorno virtual para evitar conflictos de dependencias.
- **Librerías**: utilizar el archivo `requirements.txt` para la instalación de las mismas.

> ✎ **NOTA** Asegúrese de tener instalado `git` en su máquina o `GitHub Desktop` para la clonación del repositorio. Así mismo, contar con el paquete de [NodeJS](https://nodejs.org/) instalado en su máquina. 

### Instalación de Frontend 

En una ventana de comandos (cmd/terminal), ejecutar los comandos que a continuación se describen:

**Clonar el repositorio**:

> ℹ️ Seleccione una ruta en su equipo/máquina donde desea almacenar los archivos del presente proyecto.

Clone el repositorio en su entorno local:
   ```bash
   git clone https://github.com/diegoa-rodriguezc/sistemas-recomendacion.git
   ```

Cambie al directorio del proyecto:
   ```bash
   cd Taller3
   ```

En una ventana de comandos (cmd/terminal) y ubicado en la carpeta `Taller3` proceder con los siguiente pasos:

Instalar dependencias:
   ```bash
   npm install
   ```

Ejecutar la aplicacióRun:
   ```bash
   npm run dev
   ```


### Instalación de Backend

ℹ️ En otra ventana de comandos/terminal, sin cerrar la del paso anterior ejecutar los pasos descritos a continuación.

1. Ingresar a la carpeta de `backend`:
   ```bash
   cd backend
   ```

2. Instalar la libería respectiva para crear un entorno virtual de trabajo
```bash 
pip install virtualenv
```

3. Crear un entorno virtual:
```bash 
python -m venv env
```

4. Acticar entorno virtual, previamente creado:
    * En Windows, ejecutar:
    ```bash
    .\env\Scripts\Activate.ps1
    ```
    * En Linux, ejecutar:
    ```bash
    source env/bin/activate
    ```

5. Posterior a la activación del entorno virtual, se procede a realizar la instalación de dependiencias, con el comando:
```bash
pip install -r requirements.txt
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

## Ingreso a la aplicación

Una vez se ha levantado el Frontend y el Backend, se debe ingresar a un navegador Web y acceder a la URL: `http://localhost:8081/login`


