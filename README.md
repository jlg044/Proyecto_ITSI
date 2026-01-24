# Proyecto Final — Sistema de Orquestación de Soporte Técnico

Este proyecto implementa un sistema automatizado de **recepción, clasificación y enrutamiento de tickets de soporte**. Utiliza una arquitectura de microservicios basada en containers para garantizar un flujo de trabajo eficiente y escalable.

---

## Arquitectura y Componentes

El sistema se organiza en los siguientes módulos:

- **Flask Web API (Puerto 5001)**: Interfaz de entrada para los tickets. Se encarga de la validación, persistencia en base de datos y enrutamiento inteligente.
- **PostgreSQL (Puerto 5433)**: Almacenamiento persistente de tickets y gestión de clientes VIP.
- **RabbitMQ (Puertos 5672/15672)**: Gestor de colas asíncronas con 4 niveles de prioridad.
- **Worker Service**: Servicio que procesa en segundo plano los tickets encolados.
- **n8n (Puerto 5678)**: Motor de automatización para notificaciones (Gmail) y logs de errores (Google Sheets).

---

## Instalación y Despliegue

Sigue estos pasos para levantar el entorno completo:

1. **Preparar entorno**:
   ```bash
   cp .env.example .env
   # Edita el archivo .env con tus credenciales y configuración
   ```

2. **Preparar volúmenes**:
   ```bash
   docker volume create n8n_data
   ```

3. **Levantar servicios**:
   ```bash
   docker-compose up -d
   ```

4. **Verificar**:
   ```bash
   docker-compose ps
   ```

---

## Configuración (.env)

El archivo `.env` es fundamental para conectar los servicios. Aquí los bloques principales:

- **Base de Datos**: `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB` definen el acceso a la base de datos interna.
- **RabbitMQ**: Credenciales para el broker de mensajería (por defecto `guest/guest`).
- **n8n**: Configuración del host y puerto para la interfaz de automatización.
- **Integraciones**: `GOOGLE_SHEETS_ID` y `GMAIL_EMAIL` para habilitar el reporte de errores y notificaciones al cliente.
- **Flask**: `FLASK_DEBUG=True` activa el modo desarrollo (auto-reload y errores detallados).

---

## Lógica de Enrutamiento Inteligente

El sistema clasifica cada ticket automáticamente hacia una cola de RabbitMQ según estas reglas:

| Prioridad | Condición | Cola Destino |
|-----------|-----------|--------------|
| **1** | Cliente VIP + Urgencia Alta | `queue_vip_urgent` |
| **2** | Categoría Técnica + Urgencia Alta | `queue_technical_urgent` |
| **3** | Categoría Facturación | `queue_billing` |
| **4** | Resto de casos | `queue_normal` |

---

## Guía de Pruebas (curl)

Para verificar el funcionamiento, puedes ejecutar estos comandos desde tu terminal:

### A. Registrar un Cliente como VIP
```bash
curl -X POST http://localhost:5001/clientes \
  -H "Content-Type: application/json" \
  -d '{"email": "profesor@itsi.com"}'
```

### B. Crear Ticket VIP de Alta Prioridad
```bash
curl -X POST http://localhost:5001/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "usuario": "Profesor ITSI",
    "email": "profesor@itsi.com",
    "asunto": "Consulta Crítica",
    "urgencia": "Alta",
    "categoria": "Tecnica"
  }'
```
*Este ticket se enrutará automáticamente a `queue_vip_urgent`.*

### C. Consultar Estado de las Colas
Accede al panel de RabbitMQ: [http://localhost:15672](http://localhost:15672) (user: `guest` / pass: `guest`).

---

## Enlaces del Sistema
- **API Web**: [http://localhost:5001/tickets](http://localhost:5001/tickets)
- **Panel n8n**: [http://localhost:5678](http://localhost:5678)
- **Logs del Worker**: `docker-compose logs -f worker`

---

## Autores
- Proyecto desarrollado como parte del curso ITSI.
