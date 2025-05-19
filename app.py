

from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from datetime import datetime
from flask import jsonify
import os
from dotenv import load_dotenv
app = Flask(__name__)

# ------------------ CONFIGURACIÓN DE LA BD ------------------



load_dotenv()

def conectar():
    return mysql.connector.connect(
        host=os.getenv("nozomi.proxy.rlwy.net"),
        user=os.getenv("root"),
        password=os.getenv("icXPnbNWiAioFqLRyMlbJNYaJAvyqdyV"),
        database=os.getenv("railway"),
        port=int(os.getenv("28979"))
    )


# ------------------ RUTAS ------------------

@app.route('/')
def index():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM Docentes')
    docentes = cursor.fetchall()
    conn.close()
    return render_template('index.html', docentes=docentes)



@app.route('/formularios', methods=['GET', 'POST'])
def formularios():
    conn = conectar()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        id_docente = request.form.get('id_docente')
        calificacion = request.form.get('calificacion')
        resena = request.form.get('resena')

        # Validación básica
        if not id_docente or not calificacion or not resena:
            conn.close()
            return "Faltan datos en el formulario", 400

        try:
            calificacion = float(calificacion)
            id_docente = int(id_docente)

            # Insertar directamente en la tabla Reseñas
            cursor.execute(
                'INSERT INTO Resenas (id_docente, resena, fecha, valor_calificacion) VALUES (%s, %s, %s, %s)',
                (id_docente, resena, datetime.now(), calificacion)
            )

            conn.commit()
        except Exception as e:
            conn.rollback()
            conn.close()
            return f"Error al guardar los datos: {e}", 500

        conn.close()
        return redirect(url_for('detalle_docente', id_docente=id_docente))

    # Método GET
    id_docente = request.args.get('id_docente')
    docente = None
    if id_docente:
        cursor.execute('SELECT * FROM Docentes WHERE id_docente = %s', (id_docente,))
        docente = cursor.fetchone()

    conn.close()
    return render_template('formulario.html', docente=docente)











@app.route('/buscar_docente')
def buscar_docente():
    q = request.args.get('q', '').strip()
    conn = conectar()
    cursor = conn.cursor(dictionary=True)

    if q:
        query = """
            SELECT d.*, 
                   ROUND(AVG(r.valor_calificacion), 1) AS promedio
            FROM Docentes d
            LEFT JOIN Resenas r ON d.id_docente = r.id_docente
            WHERE d.nombre LIKE %s OR d.materias LIKE %s
            GROUP BY d.id_docente
        """
        like_q = f"%{q}%"
        cursor.execute(query, (like_q, like_q))
    else:
        query = """
            SELECT d.*, 
                   ROUND(AVG(r.valor_calificacion), 1) AS promedio
            FROM Docentes d
            LEFT JOIN Resenas r ON d.id_docente = r.id_docente
            GROUP BY d.id_docente
        """
        cursor.execute(query)

    resultados = cursor.fetchall()
    conn.close()
    return jsonify(resultados)






@app.route('/docentes/<int:id_docente>')
def detalle_docente(id_docente):
    conn = conectar()
    cursor = conn.cursor(dictionary=True)
    
    # Docente
    cursor.execute("SELECT * FROM Docentes WHERE id_docente = %s", (id_docente,))
    docente = cursor.fetchone()
    if not docente:
        return "Docente no encontrado", 404
    
    # Reseñas
    cursor.execute("""
        SELECT id_resena, resena, fecha, valor_calificacion
        FROM Resenas
        WHERE id_docente = %s
        ORDER BY fecha DESC
    """, (id_docente,))
    resenas = cursor.fetchall()

    # Adjuntar comentarios a cada reseña
    for r in resenas:
        cursor.execute("""
            SELECT id_comentario, comentario, fecha
            FROM Comentarios
            WHERE id_resena = %s
            ORDER BY fecha ASC
        """, (r['id_resena'],))
        r['comentarios'] = cursor.fetchall()

    # Calcular promedio de calificaciones
    calificaciones = [float(r['valor_calificacion']) for r in resenas if r['valor_calificacion']]
    promedio = round(sum(calificaciones) / len(calificaciones), 1) if calificaciones else None

    conn.close()
    
    return render_template(
        'docente.html',
        docente=docente,
        promedio=promedio,
        resenas=resenas,
        id=id_docente
    )


@app.route('/comentar_resena/<int:id_resena>', methods=['POST'])
def comentar_resena(id_resena):
    comentario = request.form.get('comentario')

    # Validar comentario
    if not comentario or len(comentario.strip()) < 3:
        return "Comentario no válido", 400

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Comentarios (id_resena, comentario, fecha)
        VALUES (%s, %s, NOW())
    """, (id_resena, comentario))
    conn.commit()
    conn.close()

    # Redirigir de vuelta a la página del docente
    return redirect(request.referrer or url_for('detalle_docente', id_docente=id_resena))








# ------------------ MAIN ------------------

if __name__ == '__main__':
    app.run(debug=True)