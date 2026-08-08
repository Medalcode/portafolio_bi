import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def main():
    # Setup directories
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw")
    processed_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)

    random.seed(42)
    np.random.seed(42)

    # Master Data definitions
    regions = ["Norte", "Centro", "Sur", "Este", "Oeste"]
    carriers = [
        {"id": "TR-101", "nombre": "Carrier-X Express", "sla_dias": 3},
        {"id": "TR-102", "nombre": "LogiSpeed Sur", "sla_dias": 4},
        {"id": "TR-103", "nombre": "National Freight", "sla_dias": 5},
        {"id": "TR-104", "nombre": "EcoShip Direct", "sla_dias": 4},
    ]
    
    categories = [
        {"cat": "Electrónica", "sub": "Smartphones", "precio_base": 450, "costo_prod": 280},
        {"cat": "Electrónica", "sub": "Laptops", "precio_base": 850, "costo_prod": 550},
        {"cat": "Hogar", "sub": "Muebles", "precio_base": 220, "costo_prod": 110},
        {"cat": "Hogar", "sub": "Electrodomésticos", "precio_base": 310, "costo_prod": 180},
        {"cat": "Moda", "sub": "Calzado", "precio_base": 85, "costo_prod": 35},
        {"cat": "Moda", "sub": "Ropa Deportiva", "precio_base": 65, "costo_prod": 22},
    ]

    customers = [f"CLI-{1000 + i}" for i in range(150)]
    products = [f"PROD-{100 + i}" for i in range(30)]
    
    # Assign product metadata
    prod_meta = {}
    for p_id in products:
        c = random.choice(categories)
        prod_meta[p_id] = {
            "categoria": c["cat"],
            "subcategoria": c["sub"],
            "precio_base": c["precio_base"] + random.randint(-15, 25),
            "costo_prod": c["costo_prod"] + random.randint(-10, 15)
        }

    # Assign customer metadata
    cust_meta = {}
    segmentos = ["Corporativo", "Pequeña Empresa", "Consumidor Final"]
    for c_id in customers:
        cust_meta[c_id] = {
            "segmento": random.choice(segmentos),
            "region": random.choice(regions),
            "antiguedad_años": random.randint(1, 6)
        }

    # Generate 1200 shipping records from 2024 to 2026
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2026, 6, 30)
    time_delta = (end_date - start_date).days

    raw_records = []
    
    for i in range(1, 1251):
        order_id = f"PED-{10000 + i}"
        cust_id = random.choice(customers)
        prod_id = random.choice(products)
        carrier = random.choice(carriers)
        region = cust_meta[cust_id]["region"]
        
        days_offset = random.randint(0, time_delta)
        fecha_pedido = start_date + timedelta(days=days_offset)
        
        sla = carrier["sla_dias"]
        fecha_promesa = fecha_pedido + timedelta(days=sla)
        
        # Simulating Carrier-X bottleneck in region Norte
        if carrier["id"] == "TR-101" and region == "Norte":
            # 40% chance of heavy delay
            if random.random() < 0.40:
                actual_transit = sla + random.randint(3, 7)
            else:
                actual_transit = sla + random.randint(-1, 2)
        else:
            # Standard delay distribution
            if random.random() < 0.12:
                actual_transit = sla + random.randint(2, 5)
            else:
                actual_transit = sla + random.randint(-1, 1)

        actual_transit = max(1, actual_transit)
        fecha_entrega = fecha_pedido + timedelta(days=actual_transit)
        
        pm = prod_meta[prod_id]
        monto_venta = pm["precio_base"] * random.randint(1, 3)
        costo_producto = pm["costo_prod"] * random.randint(1, 3)
        costo_envio = round(random.uniform(8.5, 35.0), 2)
        
        # Status
        if fecha_entrega <= fecha_promesa:
            estado = "Entregado"
        elif random.random() < 0.85:
            estado = "Entregado"
        else:
            estado = "Cancelado"

        # Introduce some realistic anomalies in raw dataset (e.g. missing dates or nulls)
        fecha_entrega_str = fecha_entrega.strftime("%Y-%m-%d") if estado == "Entregado" else None
        
        raw_records.append({
            "id_pedido": order_id,
            "id_cliente": cust_id,
            "id_producto": prod_id,
            "id_transportista": carrier["id"],
            "region_destino": region,
            "monto_venta": monto_venta,
            "costo_envio": costo_envio,
            "costo_producto": costo_producto,
            "fecha_pedido": fecha_pedido.strftime("%Y-%m-%d"),
            "fecha_promesa": fecha_promesa.strftime("%Y-%m-%d"),
            "fecha_entrega": fecha_entrega_str,
            "estado_envio": estado
        })

    raw_df = pd.DataFrame(raw_records)
    
    # Add a few duplicate rows to clean in SQL
    raw_df = pd.concat([raw_df, raw_df.iloc[:5]], ignore_index=True)
    
    raw_file = os.path.join(raw_dir, "staging_envios.csv")
    raw_df.to_csv(raw_file, index=False)
    print(f"Generated raw dataset: {raw_file} ({len(raw_df)} rows)")

    # Build clean Star Schema tables for Power BI / DB ingestion
    # 1. Dim_Cliente
    dim_cliente = pd.DataFrame([
        {"id_cliente": c_id, "segmento": cust_meta[c_id]["segmento"], "region": cust_meta[c_id]["region"], "antiguedad_años": cust_meta[c_id]["antiguedad_años"]}
        for c_id in customers
    ])
    dim_cliente.to_csv(os.path.join(processed_dir, "Dim_Cliente.csv"), index=False)

    # 2. Dim_Producto
    dim_producto = pd.DataFrame([
        {"id_producto": p_id, "categoria": prod_meta[p_id]["categoria"], "subcategoria": prod_meta[p_id]["subcategoria"], "precio_base": prod_meta[p_id]["precio_base"], "costo_base": prod_meta[p_id]["costo_prod"]}
        for p_id in products
    ])
    dim_producto.to_csv(os.path.join(processed_dir, "Dim_Producto.csv"), index=False)

    # 3. Dim_Transportista
    dim_transportista = pd.DataFrame(carriers)
    dim_transportista.to_csv(os.path.join(processed_dir, "Dim_Transportista.csv"), index=False)

    # 4. Dim_Calendario
    date_range = pd.date_range(start="2024-01-01", end="2026-12-31")
    dim_calendario = pd.DataFrame({
        "fecha": date_range.strftime("%Y-%m-%d"),
        "año": date_range.year,
        "trimestre": date_range.quarter,
        "mes_num": date_range.month,
        "mes_nombre": date_range.strftime("%B"),
        "semana_año": date_range.isocalendar().week,
        "dia_semana": date_range.strftime("%A")
    })
    dim_calendario.to_csv(os.path.join(processed_dir, "Dim_Calendario.csv"), index=False)

    # 5. Fact_Envios (Cleaned)
    clean_fact = raw_df.drop_duplicates(subset=["id_pedido"]).copy()
    clean_fact = clean_fact[clean_fact["fecha_pedido"].notnull() & (clean_fact["monto_venta"] > 0)].copy()
    
    clean_fact["fecha_pedido_dt"] = pd.to_datetime(clean_fact["fecha_pedido"])
    clean_fact["fecha_promesa_dt"] = pd.to_datetime(clean_fact["fecha_promesa"])
    clean_fact["fecha_entrega_dt"] = pd.to_datetime(clean_fact["fecha_entrega"])
    
    clean_fact["dias_transcurridos_reales"] = (clean_fact["fecha_entrega_dt"] - clean_fact["fecha_pedido_dt"]).dt.days
    clean_fact["dias_prometidos"] = (clean_fact["fecha_promesa_dt"] - clean_fact["fecha_pedido_dt"]).dt.days
    
    def calc_indicador(row):
        if pd.isnull(row["fecha_entrega_dt"]):
            return "En Tránsito / Pendiente"
        elif row["fecha_entrega_dt"] <= row["fecha_promesa_dt"]:
            return "A Tiempo"
        else:
            return "Atrasado"

    clean_fact["indicador_cumplimiento"] = clean_fact.apply(calc_indicador, axis=1)
    clean_fact["margen_operativo_pedido"] = clean_fact["monto_venta"] - clean_fact["costo_envio"] - clean_fact["costo_producto"]
    
    clean_fact = clean_fact.drop(columns=["fecha_pedido_dt", "fecha_promesa_dt", "fecha_entrega_dt"])
    clean_fact.to_csv(os.path.join(processed_dir, "Fact_Envios.csv"), index=False)
    print(f"Generated clean Star Schema tables in {processed_dir}")

if __name__ == "__main__":
    main()
