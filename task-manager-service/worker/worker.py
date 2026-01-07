# worker/worker.py
import os
import pika
import json
import time
import sys

def main():
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    connection = None

    while not connection:     # Esperar a que RabbitMQ esté disponible
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            print("Worker: Conectado a RabbitMQ.")
        except pika.exceptions.AMQPConnectionError:
            print("Worker: Esperando a RabbitMQ...")
            time.sleep(5)

    channel = connection.channel()

    # Definir las colas que vamos a escuchar
    queues = ['queue_vip_urgent', 'queue_technical_urgent', 'queue_billing', 'queue_normal']

    for queue_name in queues:
        # Declarar cada cola CON soporte para DLX
        channel.queue_declare(
            queue=queue_name,
            durable=True,
            arguments={
                'x-dead-letter-exchange': 'dlx_exchange',
                'x-dead-letter-routing-key': 'failed'
            }
        )
        print(f"Worker: Escuchando en '{queue_name}'")

    def callback(ch, method, properties, body):
        try:
            task_data = json.loads(body)
            # Imprimir info genérica del Ticket
            print(f" [x] Recibido en {method.routing_key}: {task_data}")
            
            # Simular procesamiento
            time.sleep(1)
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Error procesando mensaje: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)

    # Suscribirse a todas las colas
    for queue_name in queues:
        channel.basic_consume(queue=queue_name, on_message_callback=callback)

    print("[*] Worker esperando mensajes. CTRL+C para salir.")
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrumpido")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
