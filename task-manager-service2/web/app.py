# web/app.py
import os
import pika
import json
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Configuración de la Base de Datos ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Modelos de la Base de Datos ---
class Tickets(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    asunto = db.Column(db.String(120), nullable=False)
    mensaje = db.Column(db.String(255), nullable=True)
    urgencia = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(120), nullable=False)
    estado = db.Column(db.Boolean, default=False)
    vip_estatus = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'usuario': self.usuario,
            'email': self.email,
            'asunto': self.asunto,
            'mensaje': self.mensaje,
            'urgencia': self.urgencia,
            'categoria': self.categoria,    
            'estado': self.estado,
            'vip_estatus': self.vip_estatus
        }

class Clientes_VIP(db.Model):
    email = db.Column(db.String(120), unique=True, nullable=False, primary_key=True)

    def to_dict(self):
        return {
            'email': self.email,
        }

# --- Configuración de RabbitMQ ---
RABBITMQ_URL = os.environ.get('RABBITMQ_URL')

def get_rabbitmq_connection():
    return pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))

def publish_message(queue_name, message):
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Declarar DLX y cola de fallos (infraestructura base)
        channel.exchange_declare(exchange='dlx_exchange', exchange_type='direct', durable=True)
        channel.queue_declare(queue='tasks_failed', durable=True)
        channel.queue_bind(exchange='dlx_exchange', queue='tasks_failed', routing_key='failed')

        # Declarar la cola destino con configuración de Dead Letter
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                'x-dead-letter-exchange': 'dlx_exchange',
                'x-dead-letter-routing-key': 'failed'
            }
        )

        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )
        connection.close()
        print(f" [x] Sent message to queue '{queue_name}'")
    except Exception as e:
        print(f"Error publishing message: {e}")

# --- Lógica de Enrutamiento ---
def determine_queue(ticket):
    # Lógica basada en reglas de n8n
    
    # 1. VIP_Alta: vip_estatus = true AND urgencia = "Alta"
    # (Mantenemos la búsqueda en BBDD como fallback para vip_estatus, por robustez)
    es_vip = ticket.vip_estatus
    if not es_vip:
        cliente_vip = Clientes_VIP.query.filter_by(email=ticket.email).first()
        if cliente_vip:
            es_vip = True

    if es_vip and ticket.urgencia == 'Alta':
        return 'queue_vip_urgent'
    
    # 2. Tecnica_Alta: categoria = "Tecnica" AND urgencia = "Alta"
    if ticket.categoria == 'Tecnica' and ticket.urgencia == 'Alta':
        return 'queue_technical_urgent'
    
    # 3. Facturacion: categoria = "Facturacion"
    if ticket.categoria == 'Facturacion':
        return 'queue_billing'
    
    # Default
    return 'queue_normal'

# --- Endpoints de la API ---

# --- CLIENTES ---
@app.route('/clientes', methods=['POST'])
def create_client():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'error': 'Email is required'}), 400
    
    existing = Clientes_VIP.query.filter_by(email=data['email']).first()
    if existing:
         return jsonify({'error': 'Client already exists', 'client': existing.to_dict()}), 409

    new_client = Clientes_VIP(
        email=data['email']
    )
    db.session.add(new_client)
    db.session.commit()
    return jsonify(new_client.to_dict()), 201

@app.route('/clientes', methods=['GET'])
def get_clients():
    clients = Clientes_VIP.query.all()
    return jsonify([c.to_dict() for c in clients])

# --- TICKETS ---
@app.route('/tickets', methods=['POST'])
def create_ticket():
    data = request.get_json()
    required_fields = ['usuario', 'email', 'asunto']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing fields'}), 400

    # Crear Ticket en BBDD
    new_ticket = Tickets(
        usuario=data['usuario'],
        email=data['email'],
        asunto=data['asunto'],
        mensaje=data.get('mensaje', ""),
        urgencia=data.get('urgencia', 'normal'),
        categoria=data.get('categoria', 'general'),
        vip_estatus=data.get('vip_estatus', False)
    )
    db.session.add(new_ticket)
    db.session.commit()
    
    # Determinar cola y publicar
    queue_name = determine_queue(new_ticket)
    publish_message(queue_name, new_ticket.to_dict())

    return jsonify({
        'ticket': new_ticket.to_dict(),
        'assigned_queue': queue_name
    }), 201

@app.route('/tickets', methods=['GET'])
def get_tickets():
    tickets = Tickets.query.all()
    return jsonify([t.to_dict() for t in tickets])

@app.route('/tickets/<int:ticket_id>/complete', methods=['PUT'])
def complete_ticket(ticket_id):
    ticket = Tickets.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    ticket.estado = True
    db.session.commit()
    
    # Publicar mensaje en RabbitMQ
    publish_message('task_completed', ticket.to_dict())
    
    return jsonify({'ticket': ticket.to_dict()}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
