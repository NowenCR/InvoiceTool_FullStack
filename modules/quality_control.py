"""
quality_control.py
==================
Módulo encargado de la validación, limpieza y detección de anomalías en los datos.

Este módulo centraliza la lógica para detectar duplicados basados en múltiples
criterios y validar formatos de datos (como fechas) según reglas de negocio
geográficas.

Estándares: Google Python Style Guide.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configuración de formatos de fecha por país/región
# Esto permite escalar si añades México, Europa, etc.
DATE_FORMAT_RULES = {
    'USA': {'format': '%m/%d/%Y', 'desc': 'MM/DD/YYYY'},
    'US': {'format': '%m/%d/%Y', 'desc': 'MM/DD/YYYY'},
    'CANADA': {'format': '%d/%m/%Y', 'desc': 'DD/MM/YYYY'},
    'CA': {'format': '%d/%m/%Y', 'desc': 'DD/MM/YYYY'},
    'DEFAULT': {'format': '%Y-%m-%d', 'desc': 'YYYY-MM-DD'}
}

def detect_complex_duplicates(
    df: pd.DataFrame, 
    criteria_columns: List[str]
) -> pd.DataFrame:
    """Detecta filas duplicadas basándose en una combinación de columnas.

    A diferencia de una búsqueda simple por ID, esta función permite definir
    que una factura es duplicada solo si, por ejemplo, coinciden el
    'Número de Factura' Y el 'Nombre del Proveedor'.

    Args:
        df (pd.DataFrame): El DataFrame con los datos a analizar.
        criteria_columns (List[str]): Lista de nombres de columnas que, combinadas,
                                      forman la clave única (ej. ['Invoice #', 'Vendor']).

    Returns:
        pd.DataFrame: Un DataFrame que contiene solo las filas duplicadas encontradas,
                      ordenadas por las columnas de criterio para fácil comparación.
    """
    if df.empty or not criteria_columns:
        return pd.DataFrame()

    # Validamos que las columnas existan
    valid_cols = [c for c in criteria_columns if c in df.columns]
    if not valid_cols:
        return pd.DataFrame()

    # keep=False marca TODAS las apariciones del duplicado (original y copia)
    duplicates_mask = df.duplicated(subset=valid_cols, keep=False)
    
    # Filtramos y ordenamos para que el usuario vea los pares juntos
    result_df = df[duplicates_mask].sort_values(by=valid_cols)
    
    return result_df


def validate_dates_by_origin(
    df: pd.DataFrame, 
    date_col: str, 
    origin_col: str
) -> List[Dict[str, Any]]:
    """Valida el formato de fechas cruzando información con el país de origen.

    Itera sobre el DataFrame y verifica si la fecha cumple con el formato
    esperado para el país indicado en 'origin_col'.

    Args:
        df (pd.DataFrame): DataFrame de datos.
        date_col (str): Nombre de la columna que contiene la fecha de la factura.
        origin_col (str): Nombre de la columna que indica el país (ej. 'Entity Country').

    Returns:
        List[Dict[str, Any]]: Lista de errores encontrados. Cada diccionario contiene:
            - row_id: Identificador de la fila.
            - expected: Formato esperado.
            - actual: Valor encontrado.
            - reason: Explicación del error.
    """
    errors = []

    # Validar existencia de columnas
    if date_col not in df.columns or origin_col not in df.columns:
        return [{'error': 'Columnas no encontradas en el archivo'}]

    # Iteramos fila por fila (necesario para validación lógica compleja)
    # Nota: Para millones de datos, esto se debería vectorizar, pero para validación
    # de errores puntual, la iteración es segura y clara.
    for index, row in df.iterrows():
        raw_date = str(row[date_col]).strip()
        origin = str(row[origin_col]).strip().upper()
        row_id = row.get('_row_id', index)

        # Si no hay fecha, saltamos o marcamos como vacío (depende de la regla)
        if not raw_date or raw_date.lower() in ['nan', 'nat', '']:
            continue

        # Determinar regla a usar
        rule = DATE_FORMAT_RULES.get(origin, DATE_FORMAT_RULES['DEFAULT'])
        fmt = rule['format']
        
        try:
            # Intentamos convertir la fecha usando el formato estricto del país
            datetime.strptime(raw_date, fmt)
        except ValueError:
            # Si falla, es un error de formato
            errors.append({
                'row_id': row_id,
                'origin': origin,
                'date_col': date_col,
                'invalid_value': raw_date,
                'expected_format': rule['desc'],
                'message': f"Formato inválido para {origin}. Se espera {rule['desc']}."
            })

    return errors