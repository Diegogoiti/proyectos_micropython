from machine import Pin #,TouchPad
import time
import sys


# Configuración
dat = Pin(12, Pin.IN, Pin.PULL_UP)  # DATA (recibe datos y ACK)
cmd = Pin(13, Pin.OUT)             # CMD (envía órdenes)
att = Pin(14, Pin.OUT)             # ATT (selección)
clk = Pin(15, Pin.OUT)             # CLK (reloj)

#pin_stop = TouchPad(Pin(4))  # Pin táctil para resetear el mando

# Estado inicial (reposo)
att.value(1) # ATT en HIGH significa mando "deselecto"
clk.value(1) # CLK en HIGH en reposo
cmd.value(1)

def transferir_byte(byte_enviar):
    byte_recibido = 0
    for i in range(8):
        cmd.value((byte_enviar >> i) & 1)
        clk.value(0)
        time.sleep_us(20)
        if dat.value() == 0:
            byte_recibido |= (1 << i)
        clk.value(1)
        time.sleep_us(20)
    return byte_recibido
        
def leer_mando():
    att.value(0)
    time.sleep_us(20)
    # Bytes iniciales
    res = [transferir_byte(0x01), transferir_byte(0x42), transferir_byte(0x00)]
    
    # Lee los bytes de botones (añade más transferencias)
    for _ in range(6): 
        res.append(transferir_byte(0x00))
        
    att.value(1)
    return res

def leer_mando_bin():
    for i in leer_mando():
        print(f"{i:08b}", end=' ')
        print("")

def enviar_datos(analogico, b_cruceta, b_accion, lx, ly, rx, ry):
    # Esto envía los bytes directamente al flujo de salida del USB
    if analogico == 140:
        if lx == 255: lx = 254
        if ly == 255: ly = 254
        if rx == 255: rx = 254
        if ry == 255: ry = 254
    else:
        lx = 128
        ly = 128
        rx = 128
        ry = 125
    buffer = bytes([0xFF, b_cruceta, b_accion, lx, ly, rx, ry])
    sys.stdout.buffer.write(buffer)


def configurar_modo_analogico():
    # 1. Entrar en modo configuración
    att.value(0)
    time.sleep_us(20)
    transferir_byte(0x01)
    transferir_byte(0x43) # Comando para entrar en config
    transferir_byte(0x00)
    transferir_byte(0x01) # Entrar
    transferir_byte(0x00)
    att.value(1)
    time.sleep_ms(16)

    # 2. Forzar modo analógico y bloquear el botón "Analog"
    att.value(0)
    time.sleep_us(20)
    transferir_byte(0x01)
    transferir_byte(0x44) # Comando para setear modo
    transferir_byte(0x00)
    transferir_byte(0x01) # 0x01 = Analógico (0x00 = Digital)
    transferir_byte(0x03) # 0x03 = Bloquear el botón para que el usuario no lo apague
    # Completar los bytes restantes del frame de config
    for _ in range(4): 
        transferir_byte(0x00)
    att.value(1)
    time.sleep_ms(16)

    # 3. Salir del modo configuración
    att.value(0)
    time.sleep_us(20)
    transferir_byte(0x01)
    transferir_byte(0x43)
    transferir_byte(0x00)
    transferir_byte(0x00) # 0x00 = Salir
    for _ in range(5):
        transferir_byte(0x00)
    att.value(1)
    time.sleep_ms(16)

def run():

    while True:
        time.sleep_ms(5)

        data = leer_mando() # Obtienes los 9 bytes
        if data[1] == 190:
            configurar_modo_analogico()

        # Extraes solo lo que necesitas (ejemplo: botones + sticks)
        analogico = data[1]
        b_cruceta = data[3]
        b_accion = data[4]
        st_izq_x = data[5]
        st_izq_y = data[6]
        st_der_x = data[7]
        st_der_y = data[8]
        
        enviar_datos(analogico,b_cruceta, b_accion, st_izq_x, st_izq_y, st_der_x, st_der_y)
        #print(data)
        #print(f"{b_cruceta},{b_accion}, {st_izq_x}, {st_izq_y}, {st_der_x}, {st_der_y}")
        
        


run()