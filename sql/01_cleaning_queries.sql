-- =============================================================================
-- PROYECTO BI & BUSINESS INTELLIGENCE: ANÁLISIS LOGÍSTICO Y OPERATIVO DE ENVÍOS
-- Script 01: Limpieza, Transformación ETL y Preparación de Datos (PostgreSQL / MySQL)
-- Autor: Jonatthan Medalla
-- =============================================================================

-- 1. Deduplicación y Limpieza en Capa Staging mediante CTEs
WITH staging_dedup AS (
    SELECT 
        id_pedido,
        id_cliente,
        id_producto,
        id_transportista,
        region_destino,
        monto_venta,
        costo_envio,
        costo_producto,
        CAST(fecha_pedido AS DATE) AS fecha_pedido,
        CAST(fecha_promesa AS DATE) AS fecha_promesa,
        CAST(fecha_entrega AS DATE) AS fecha_entrega,
        COALESCE(estado_envio, 'Desconocido') AS estado_envio,
        -- Window Function: Identificar registros duplicados manteniendo el primer ingreso
        ROW_NUMBER() OVER(
            PARTITION BY id_pedido 
            ORDER BY fecha_pedido ASC
        ) AS rn
    FROM staging_envios
    WHERE fecha_pedido IS NOT NULL 
      AND monto_venta > 0
),
envios_filtrados AS (
    SELECT *
    FROM staging_dedup
    WHERE rn = 1
),

-- 2. Cálculo de Lead Times, Indicadores SLA y Márgenes por Pedido
envios_calculados AS (
    SELECT 
        id_pedido,
        id_cliente,
        id_producto,
        id_transportista,
        region_destino,
        fecha_pedido,
        fecha_promesa,
        fecha_entrega,
        estado_envio,
        monto_venta,
        costo_envio,
        costo_producto,
        
        -- Lead Times en días calendario
        (fecha_entrega - fecha_pedido) AS dias_transcurridos_reales,
        (fecha_promesa - fecha_pedido) AS dias_prometidos,
        
        -- Flag de cumplimiento SLA (OTDR Target)
        CASE 
            WHEN fecha_entrega IS NULL THEN 'En Tránsito / Pendiente'
            WHEN fecha_entrega <= fecha_promesa THEN 'A Tiempo'
            ELSE 'Atrasado'
        END AS indicador_cumplimiento,
        
        -- Cálculo del Margen Operativo directo por pedido
        (monto_venta - costo_envio - costo_producto) AS margen_operativo_pedido
    FROM envios_filtrados
),

-- 3. Métricas Avanzadas con Window Functions (Ranking de Clientes y Promedio Móvil)
envios_con_analytics AS (
    SELECT 
        *,
        -- Window Function 1: Recurrencia del cliente (Orden de compra cronológico)
        ROW_NUMBER() OVER(
            PARTITION BY id_cliente 
            ORDER BY fecha_pedido ASC
        ) AS orden_compra_cliente,
        
        -- Window Function 2: Promedio móvil a 30 días del tiempo de entrega por transportista
        AVG(dias_transcurridos_reales) OVER(
            PARTITION BY id_transportista 
            ORDER BY fecha_pedido 
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS avg_movil_dias_entrega
    FROM envios_calculados
)

-- 4. Selección Final Estructurada para Vista o Ingesta a Data Warehouse / Power BI
SELECT 
    id_pedido,
    id_cliente,
    id_producto,
    id_transportista,
    region_destino,
    fecha_pedido,
    fecha_promesa,
    fecha_entrega,
    estado_envio,
    indicador_cumplimiento,
    monto_venta,
    costo_envio,
    costo_producto,
    margen_operativo_pedido,
    dias_transcurridos_reales,
    dias_prometidos,
    orden_compra_cliente,
    ROUND(CAST(avg_movil_dias_entrega AS NUMERIC), 2) AS avg_movil_dias_entrega
FROM envios_con_analytics;
