-- Crear tabla Tickets
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL,
    asunto VARCHAR(120) NOT NULL,
    mensaje VARCHAR(255),
    urgencia VARCHAR(120) NOT NULL,
    categoria VARCHAR(120) NOT NULL,
    estado BOOLEAN DEFAULT FALSE,
    vip_estatus BOOLEAN DEFAULT FALSE
);

-- Crear tabla Clientes_VIP
CREATE TABLE IF NOT EXISTS clientes_vip (
    email VARCHAR(120) UNIQUE NOT NULL PRIMARY KEY
);

-- Crear índices para mejora de rendimiento
CREATE INDEX IF NOT EXISTS idx_tickets_email ON tickets(email);
CREATE INDEX IF NOT EXISTS idx_tickets_estado ON tickets(estado);
CREATE INDEX IF NOT EXISTS idx_tickets_vip_estatus ON tickets(vip_estatus);
