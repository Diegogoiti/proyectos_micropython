#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serialport;
use std::thread;
use std::time::Duration;
use vigem_client::{Client, XButtons, XGamepad, Xbox360Wired};

// Mapeos estáticos de botones de Xbox 360
const CRUCETA_MAP: [u16; 8] = [
    0x0020, // Bit 0: Select (BACK)
    0x0040, // Bit 1: L3 (LEFT_THUMB)
    0x0080, // Bit 2: R3 (RIGHT_THUMB)
    0x0010, // Bit 3: Start (START)
    0x0001, // Bit 4: Arriba (UP)
    0x0008, // Bit 5: Derecha (RIGHT)
    0x0002, // Bit 6: Abajo (DOWN)
    0x0004, // Bit 7: Izquierda (LEFT)
];

const ACCION_MAP: [u16; 8] = [
    0,      // Bit 0: L2 (Trigger analógico)
    0,      // Bit 1: R2 (Trigger analógico)
    0x0100, // Bit 2: L1 (LEFT_SHOULDER)
    0x0200, // Bit 3: R1 (RIGHT_SHOULDER)
    0x8000, // Bit 4: Triángulo (Y)
    0x2000, // Bit 5: Círculo (B)
    0x1000, // Bit 6: Equis (A)
    0x4000, // Bit 7: Cuadrado (X)
];

// Identificadores de hardware USB comunes del ESP32 (CP210x o CH340)
const ESP32_VID: u16 = 0x10C4;
const ESP32_PID: u16 = 0xEA60;

fn buscar_puerto_esp32() -> Option<String> {
    if let Ok(ports) = serialport::available_ports() {
        for p in ports {
            if let serialport::SerialPortType::UsbPort(usb_info) = p.port_type {
                if usb_info.vid == ESP32_VID || usb_info.pid == ESP32_PID {
                    return Some(p.port_name);
                }
            }
        }
    }
    None
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // 1. Inicializar ViGEmBus
    let client = Client::connect()?;
    let mut target = Xbox360Wired::new(client, vigem_client::TargetId::XBOX360_WIRED);
    target.plugin()?;
    target.wait_ready()?;

    loop {
        if let Some(puerto_com) = buscar_puerto_esp32() {
            let port_result = serialport::new(&puerto_com, 115200)
                .timeout(Duration::from_millis(50))
                .open();

            match port_result {
                Ok(mut port) => {
                    let _ = port.clear(serialport::ClearBuffer::All);

                    let mut header = [0u8; 1];
                    let mut data = [0u8; 6];

                    // Bucle principal de procesamiento de inputs
                    loop {
                        // Sincronización con el Header bloqueante
                        if port.read_exact(&mut header).is_ok() && header[0] == 0xFF {
                            if port.read_exact(&mut data).is_ok() {
                                let cruceta = data[0];
                                let accion = data[1];
                                let rx = data[2];
                                let ry = data[3];
                                let lx = data[4];
                                let ly = data[5];

                                // --- Mapeo de Botones (Corregido a Lógica Normal: 1 = Presionado) ---
                                let mut raw_buttons = 0u16;
                                for bit in 0..8 {
                                    if ((cruceta >> bit) & 1) == 1 {
                                        raw_buttons |= CRUCETA_MAP[bit];
                                    }
                                    if ((accion >> bit) & 1) == 1 {
                                        raw_buttons |= ACCION_MAP[bit];
                                    }
                                }

                                // --- Triggers Binarios (Corregido a Lógica Normal) ---
                                let left_trigger = if ((accion >> 0) & 1) == 1 { 255 } else { 0 };
                                let right_trigger = if ((accion >> 1) & 1) == 1 { 255 } else { 0 };

                                let left_thumb_x =
                                    ((128 - lx as i32) * 256).clamp(-32768, 32767) as i16;
                                let left_thumb_y =
                                    ((ly as i32 - 128) * 256).clamp(-32768, 32767) as i16;

                                // STICK DERECHO (Mapeado a datos RX y RY)
                                let right_thumb_x =
                                    ((128 - rx as i32) * 256).clamp(-32768, 32767) as i16;
                                let right_thumb_y =
                                    ((ry as i32 - 128) * 256).clamp(-32768, 32767) as i16;

                                // --- CONSTRUIR ESTADO DEL GAMEPAD ---

                                // Construir el reporte del mando virtual
                                let state = XGamepad {
                                    buttons: XButtons(raw_buttons),
                                    left_trigger,
                                    right_trigger,
                                    thumb_lx: left_thumb_x, // Asignado correctamente al Izquierdo
                                    thumb_ly: left_thumb_y, // Asignado correctamente al Izquierdo
                                    thumb_rx: right_thumb_x, // Asignado correctamente al Derecho
                                    thumb_ry: right_thumb_y, // Asignado correctamente al Derecho
                                };

                                // Enviar datos directos al driver de Windows
                                let _ = target.update(&state);
                                port.clear(serialport::ClearBuffer::All)?; // esta es la linea agregada
                            }
                        } else if port.read_exact(&mut header).is_err() {
                            break;
                        } else {
                            port.clear(serialport::ClearBuffer::All)?;
                        }
                    }
                }
                Err(_) => {
                    thread::sleep(Duration::from_millis(250));
                }
            }
        }
        thread::sleep(Duration::from_secs(1));
    }
}
