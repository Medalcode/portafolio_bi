-- =============================================================================
-- PROYECTO BI & BUSINESS INTELLIGENCE: ANÁLISIS LOGÍSTICO Y OPERATIVO DE ENVÍOS
-- Script 02: Consultas Analíticas Avanzadas, Vistas de KPIs & Benchmarking SLA
-- Autor: Jonatthan Medalla
-- =============================================================================

-- -----------------------------------------------------------------------------
-- VISTA 1: Desempeño Operativo y SLA por Transportista (Carrier Performance)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_transportistas AS
SELECT 
    t.nombre AS transportista,
    COUNT(f.id_pedido) AS total_pedidos,
    SUM(CASE WHEN f.estado_envio = 'Entregado' THEN 1 ELSE 0 END) AS pedidos_entregados,
    SUM(CASE WHEN f.indicador_cumplimiento = 'A Tiempo' THEN 1 ELSE 0 END) AS pedidos_a_tiempo,
    SUM(CASE WHEN f.indicador_cumplimiento = 'Atrasado' THEN 1 ELSE 0 END) AS pedidos_atrasados,
    
    -- On-Time Delivery Rate (OTDR %)
    ROUND(
        (SUM(CASE WHEN f.indicador_cumplimiento = 'A Tiempo' THEN 1 ELSE 0 END)::NUMERIC / 
         NULLIF(SUM(CASE WHEN f.estado_envio = 'Entregado' THEN 1 ELSE 0 END), 0)) * 100, 2
    ) AS otdr_porcentaje,
    
    -- Promedio de Días Reales vs Prometidos
    ROUND(AVG(f.dias_transcurridos_reales)::NUMERIC, 2) AS promedio_dias_reales,
    ROUND(AVG(f.dias_prometidos)::NUMERIC, 2) AS promedio_dias_prometidos,
    
    -- Margen Operativo Total generado por Transportista
    ROUND(SUM(f.margen_operativo_pedido)::NUMERIC, 2) AS margen_operativo_total
FROM Fact_Envios f
JOIN Dim_Transportista t ON f.id_transportista = t.id
GROUP BY t.nombre;

-- -----------------------------------------------------------------------------
-- VISTA 2: Detección de Cuellos de Botella por Región y Transportista (Cross-Analysis)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_cuellos_botella_region AS
SELECT 
    f.region_destino,
    t.nombre AS transportista,
    COUNT(f.id_pedido) AS volumen_pedidos,
    ROUND(AVG(f.dias_transcurridos_reales)::NUMERIC, 2) AS lead_time_promedio,
    ROUND(
        (SUM(CASE WHEN f.indicador_cumplimiento = 'Atrasado' THEN 1 ELSE 0 END)::NUMERIC / 
         COUNT(f.id_pedido)) * 100, 2
    ) AS tasa_retraso_pct,
    ROUND(SUM(f.costo_envio)::NUMERIC, 2) AS costo_envio_acumulado
FROM Fact_Envios f
JOIN Dim_Transportista t ON f.id_transportista = t.id
GROUP BY f.region_destino, t.nombre
ORDER BY tasa_retraso_pct DESC;

-- -----------------------------------------------------------------------------
-- CONSULTA 3: Comparativa Interanual (Year-over-Year - YoY) en SQL usando LAG()
-- -----------------------------------------------------------------------------
WITH resumen_mensual AS (
    SELECT 
        EXTRACT(YEAR FROM fecha_pedido) AS anio,
        EXTRACT(MONTH FROM fecha_pedido) AS mes,
        SUM(monto_venta) AS ventas_totales,
        SUM(margen_operativo_pedido) AS margen_total,
        COUNT(id_pedido) AS volumen_pedidos
    FROM Fact_Envios
    GROUP BY EXTRACT(YEAR FROM fecha_pedido), EXTRACT(MONTH FROM fecha_pedido)
)
SELECT 
    anio,
    mes,
    ventas_totales,
    LAG(ventas_totales, 12) OVER(ORDER BY anio, mes) AS ventas_anio_anterior,
    ROUND(
        ((ventas_totales - LAG(ventas_totales, 12) OVER(ORDER BY anio, mes)) / 
         NULLIF(LAG(ventas_totales, 12) OVER(ORDER BY anio, mes), 0)) * 100, 2
    ) AS crecimiento_yoy_pct,
    margen_total
FROM resumen_mensual
ORDER BY anio DESC, mes DESC;
