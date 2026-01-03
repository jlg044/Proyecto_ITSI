import os
import pika
import json
import time
import requests

def main():
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    webhook_url = os.environ.get('WEBHOOK_URL')
    
    connection = None

    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            print("Notifier: Conectado a RabbitMQ.")
        except pika.exceptions.AMQPConnectionError:
            print("Notifier: Esperando a RabbitMQ...")
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue='task_completed', durable=True)

    def callback(ch, method, properties, body):
        task_data = json.loads(body)
        
        print(f"[+] Notifier recibió tarea completada: {task_data}")

        # Simular envío de email mediante POST
        try:
            requests.post(webhook_url, json=task_data)
            print("[+] Email enviado correctamente")
        except Exception as e:
            print(f"[!] Error enviando email: {e}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='task_completed', on_message_callback=callback)

    print("Notifier esperando mensajes... CTRL+C para salir.")
    channel.start_consuming()

if __name__ == "__main__":
    main()