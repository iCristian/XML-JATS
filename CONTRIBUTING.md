# Contribuir al Proyecto

¡Gracias por tu interés en mejorar el Transformador XML JATS! Este documento describe las normas y mejores prácticas para contribuir al código.

## Configuración del Entorno de Desarrollo

1. **Clonar el repositorio**:

    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_DEL_DIR>
    ```

2. **Crear un entorno virtual** (Python 3.9+ recomendado):

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    ```

3. **Instalar dependencias**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Configurar Variables de Entorno**:
    Asegúrate de tener acceso a la CLI de Gemini o configurar la variable `GEMINI_API_KEY` si el código lo requiere directamente.

## Estilo de Código y Normas

Para mantener la calidad y legibilidad del código, exigimos el cumplimiento de las siguientes normas en todos los Pull Requests:

### 1. Convenciones Generales

- Seguimos **PEP 8**.
- Longitud de línea máxima sugerida: **100 caracteres**.
- Usa **snake_case** para funciones y variables, y **PascalCase** para clases.

### 2. Type Hints (Tipado Estático)

Todas las funciones y métodos **deben** tener anotaciones de tipo (Type Hints) completas para argumentos y valores de retorno.

**Correcto:**

```python
def procesar_texto(entrada: str, opciones: Dict[str, bool]) -> List[str]:
    ...
```

**Incorrecto:**

```python
def procesar_texto(entrada, opciones):
    ...
```

### 3. Docstrings (Estilo Google)

Todas las funciones, clases y módulos públicos deben tener docstrings siguiendo el **Google Python Style Guide**.

**Ejemplo:**

```python
def funcion_ejemplo(arg1: int, arg2: str) -> bool:
    """Realiza una operación de ejemplo.

    Explica brevemente qué hace la función. Puede tener múltiples líneas
    si es complejo.

    Args:
        arg1 (int): El primer argumento, que representa X.
        arg2 (str): El segundo argumento, que representa Y.

    Returns:
        bool: True si la operación fue exitosa, False en caso contrario.

    Raises:
        ValueError: Si arg1 es negativo.
    """
    ...
```

## Flujo de Trabajo

1. **Reportar Problemas**: Abre un Issue antes de comenzar trabajos grandes.
2. **Ramas (Branches)**: Crea ramas descriptivas, ej. `feature/validacion-xml` o `fix/error-parseo`.
3. **Pull Requests**:
    - Describe claramente tus cambios.
    - Asegúrate de que el código pase las validaciones locales.
    - Adjunta capturas de pantalla si cambiaste la interfaz gráfica.

## Contacto

Para dudas técnicas, contacta a: [cristian.carreno@uv.cl](mailto:cristian.carreno@uv.cl)
Universidad de Valparaíso.
