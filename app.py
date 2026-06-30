from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import random
import os
# 1. CREA LA INSTANCIA DE LA APP
app = Flask(__name__)
# 2. ACTIVA CORS
CORS(app)

# 3. AHORA SI, TUS RUTAS (El decorador ya reconocerá 'app')
@app.route('/api/captcha', methods=['GET'])
def generar_captcha():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    resultado = num1 + num2
    return jsonify({"num1": num1, "num2": num2, "resultado": resultado})

def obtener_conexion():
    # Si existe DATABASE_URL (Railway), la usamos
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return psycopg2.connect(database_url)

    # Si no existe, usa la base de datos local
    return psycopg2.connect(
        host="localhost",
        database="motoshield_bd",
        user="postgres",
        password="qwerty",
        port=5432
    )

# 1. RUTA DEL DASHBOARD
@app.route('/api/dashboard', methods=['GET'])
def cargar_dashboard():
    return jsonify({
        "usuario": "Lourdes Serrano",
        "rol": "administrador",
        "estadisticas": {
            "dispositivos_activos": 1,
            "alertas_criticas": 0,
            "ventas_mes": "Bs. 0"
        }
    }), 200

# 2. RUTA DE INVENTARIO: REGISTRAR MÓDULO IOT
@app.route('/api/productos', methods=['POST'])
def registrar_producto():
    try:
        datos = request.get_json(force=True)
        modelo_iot = datos.get('modelo_iot')
        codigo_imei = datos.get('codigo_imei')
        
        if not modelo_iot or not codigo_imei:
            return jsonify({"error": "Faltan campos obligatorios"}), 400
            
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        query = """
            INSERT INTO dispositivos_gps (modelo_iot_hardware, codigo_imei, estado_dispositivo) 
            VALUES (%s, %s, 'disponible') RETURNING id_gps;
        """
        cursor.execute(query, (modelo_iot, codigo_imei))
        id_generado = cursor.fetchone()[0]
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        return jsonify({"status": "ok", "id": id_generado}), 201
    except Exception as error:
        return jsonify({"error": str(error)}), 500

# 3. RUTA DE MONITOREO / SIMULADOR IOT
@app.route('/api/monitoreo-iot', methods=['POST'])
def simular_rastreo_moto():
    try:
        datos = request.get_json(force=True)
        id_gps = datos.get('id_gps', 1) 
        latitud = float(datos.get('latitud', -21.5284)) 
        longitud = float(datos.get('longitud', -64.7298))
        bateria_gps = datos.get('bateria_gps', '95%')
        estado_motor = datos.get('estado_motor', 'Apagado')
        
        # Algoritmo de Geocerca del Campus Central UAJMS
        dentro_uajms = (-21.5320 <= latitud <= -21.5250) and (-64.7330 <= longitud <= -64.7260)
        geocerca_estado = "Dentro del Campus UAJMS" if dentro_uajms else "¡ALERTA! Fuera del Perímetro Autorizado"
        seguridad_status = "seguro" if dentro_uajms else "alerta"
        
        return jsonify({
            "status": "ok",
            "id_gps": id_gps,
            "geocerca": geocerca_estado,
            "seguridad": seguridad_status,
            "bateria": bateria_gps,
            "motor": estado_motor,
            "coordenadas": f"{latitud}, {longitud}"
        }), 200
    except Exception as error:
        return jsonify({"error": str(error)}), 500

# 4. RUTA PARA LISTAR DISPOSITIVOS EN UNA TABLA
@app.route('/api/obtener-productos', methods=['GET'])
def obtener_productos_almacen():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        query = "SELECT id_gps, modelo_iot_hardware, codigo_imei, estado_dispositivo FROM dispositivos_gps ORDER BY id_gps DESC;"
        cursor.execute(query)
        filas = cursor.fetchall()
        
        lista_productos = []
        for fila in filas:
            lista_productos.append({
                "id_gps": fila[0],
                "modelo_iot": fila[1],
                "codigo_imei": fila[2],
                "estado": fila[3]
            })
            
        cursor.close()
        conexion.close()
        return jsonify(lista_productos), 200
    except Exception as error:
        return jsonify({"error": str(error)}), 500

@app.route('/api/motos-activas', methods=['GET'])
def motos_activas():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT
                p.nombre_completo,
                d.id_gps
            FROM perfiles_estudiantes p
            JOIN ventas_suscripciones v
                ON p.id_estudiante=v.id_estudiante
            JOIN dispositivos_gps d
                ON d.estado_dispositivo='instalado'
            ORDER BY p.nombre_completo;
        """)

        filas = cursor.fetchall()

        lista=[]

        for fila in filas:

            lista.append({

                "nombre":fila[0],
                "gps":fila[1],
                "estado":"EN CUMPLIMIENTO",
                "lat":"-21.5284",
                "lng":"-64.7298"

            })

        cursor.close()
        conexion.close()

        return jsonify(lista)

    except Exception as e:

        return jsonify({"error":str(e)}),500

# 5. RUTA DE VENTAS: REGISTRAR UNA TRANSACCIÓN
@app.route('/api/registrar-venta', methods=['POST'])
def registrar_venta():
    try:
        datos = request.get_json(force=True)
        id_gps = datos.get('id_gps')
        estudiante = datos.get('estudiante')
        ru = datos.get('ru')  
        monto = datos.get('monto', 350.00) 
        
        if not id_gps or not estudiante or not ru:
            return jsonify({"error": "Faltan campos obligatorios"}), 400
            
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        query_estudiante = """
            INSERT INTO perfiles_estudiantes (nombre_completo, registro_universitario, celular_contacto)
            VALUES (%s, %s, '71100000')
            ON CONFLICT (registro_universitario) DO UPDATE SET nombre_completo = EXCLUDED.nombre_completo
            RETURNING id_estudiante;
        """
        cursor.execute(query_estudiante, (estudiante, ru))
        id_estudiante_gen = cursor.fetchone()[0]
        
        query_venta = """
            INSERT INTO ventas_suscripciones (id_estudiante, monto_total_bs) 
            VALUES (%s, %s) RETURNING id_venta;
        """
        cursor.execute(query_venta, (id_estudiante_gen, monto))
        id_venta_generada = cursor.fetchone()[0]
        
        query_update_gps = """
            UPDATE dispositivos_gps  
            SET estado_dispositivo = 'instalado' 
            WHERE id_gps = %s;
        """
        cursor.execute(query_update_gps, (id_gps,))
        
        conexion.commit()
        cursor.close()
        conexion.close()
        
        return jsonify({
            "status": "ok",
            "message": "Venta completada y módulo IoT activado",
            "id_venta": id_venta_generada
        }), 201
        
    except Exception as error:
        return jsonify({"error": str(error)}), 500

# 6. ENDPOINT PARA INICIAR SESIÓN (CORREGIDO)
@app.route('/api/login', methods=['POST'])
def login():
    try:
        datos = request.json
        usuario = datos.get('usuario')
        clave = datos.get('clave')
        rol_seleccionado = datos.get('rol_seleccionado') # Nuevo: recibimos el rol del select

        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Consultamos el usuario y su rol real en la BD
        cursor.execute("SELECT nombre, rol FROM usuarios WHERE usuario = %s AND clave = %s", (usuario, clave))
        resultado = cursor.fetchone()
        
        cursor.close()
        conexion.close()

        if resultado:
            nombre_db = resultado[0]
            rol_db = resultado[1]
            
            # VALIDACIÓN DE SEGURIDAD: Comparar el rol seleccionado con el de la BD
            if rol_db == rol_seleccionado:
                return jsonify({
                    "valido": True,
                    "nombre": nombre_db,
                    "rol": rol_db
                }), 200
            else:
                return jsonify({"valido": False, "mensaje": "Acceso denegado: El tipo de cuenta no coincide con su perfil."}), 403
        else:
            return jsonify({"valido": False, "mensaje": "Usuario o contraseña incorrectos"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ==========================================
# ENDPOINT ADICIONAL PARA ADMINISTRADORES
# ==========================================
@app.route('/api/obtener-usuarios', methods=['GET'])
def obtener_usuarios_sistema():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # Consultamos los usuarios registrados en el sistema
        query = "SELECT id_usuario, nombre, usuario, rol FROM usuarios ORDER BY id_usuario DESC;"
        cursor.execute(query)
        filas = cursor.fetchall()
        
        lista_usuarios = []
        for fila in filas:
            lista_usuarios.append({
                "id_usuario": fila[0],
                "nombre": fila[1],
                "usuario": fila[2],
                "rol": fila[3]
            })
            
        cursor.close()
        conexion.close()
        return jsonify(lista_usuarios), 200
    except Exception as error:
        if 'conexion' in locals() and conexion:
            conexion.close()
        return jsonify({"error": str(error)}), 500

# 7. ENDPOINT PARA REGISTRAR USUARIOS (CORREGIDO)
@app.route('/api/registrar', methods=['POST'])
def registrar_usuario():
    try:
        conexion = obtener_conexion() 
        cursor = conexion.cursor()
    
        datos = request.json
        nombre = datos.get('nombre')
        usuario = datos.get('usuario')
        clave = datos.get('clave')
        rol = datos.get('rol') 
        
        cursor.execute(
            "INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES (%s, %s, %s, %s)",
            (nombre, usuario, clave, rol)
        )
        
        conexion.commit()
        cursor.close()
        conexion.close() 
        
        return jsonify({"mensaje": f"Usuario con rol '{rol}' registrado con éxito"}), 201
    except Exception as e:
        if 'conexion' in locals() and conexion:
            conexion.close()
        return jsonify({"error": str(e)}), 400


# 8. ENDPOINT PARA REGISTRAR MOTOCICLETAS (YA NO ESTÁ ANIDADO)
@app.route('/api/motocicletas', methods=['POST'])
def registrar_motocicleta():

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        datos = request.json
        ru = datos.get('ru')
        id_especificacion = datos.get('id_especificacion', 1) # Captura el ID del select
        placa = datos.get('placa')
        numero_chasis = datos.get('numero_chasis')
        color_predominante = datos.get('color_predominante')
        anio_modelo = datos.get('anio_modelo')

        # Buscamos el id_estudiante usando el RU
        cursor.execute("SELECT id_estudiante FROM perfiles_estudiantes WHERE registro_universitario = %s", (ru,))
        estudiante = cursor.fetchone()
        
        if not estudiante:
            cursor.execute(
                "INSERT INTO perfiles_estudiantes (nombre_completo, registro_universitario, celular_contacto) VALUES (%s, %s, '71100000') RETURNING id_estudiante",
                ('Estudiante UAJMS', ru)
            )
            id_estudiante = cursor.fetchone()[0]
        else:
            id_estudiante = estudiante[0]

        # Insertamos usando las relaciones relacionales de tu esquema en 3FN
        cursor.execute("""
            INSERT INTO motocicletas (id_estudiante, id_especificacion, placa_motocicleta, color_predominante, numero_chasis, anio_modelo)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_moto
        """, (id_estudiante, id_especificacion, placa, color_predominante, numero_chasis, anio_modelo))
        
        id_moto = cursor.fetchone()[0]
        conexion.commit()
        cursor.close()
        conexion.close()

        return jsonify({"mensaje": "Motocicleta añadida exitosamente", "id_moto": id_moto}), 201

    except Exception as e:
        if 'conexion' in locals() and conexion:
            conexion.rollback()
            conexion.close()
        return jsonify({"error": str(e)}), 400



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)