import mido

def midi_a_hz(nota):
    return int(440 * (2 ** ((nota - 69) / 12)))

def extraer_melodia(archivo_midi, pista_idx=0, silencio_ms=30):
    mid = mido.MidiFile(archivo_midi)
    print(f"Número de pistas: {len(mid.tracks)}")
    notas = []
    
    notas_activas = {}
    tiempo_absoluto = 0
    
    pista = mid.tracks[pista_idx]
    
    for msg in pista:
        tiempo_absoluto += msg.time
        
        if msg.type == 'note_on' and msg.velocity > 0:
            notas_activas[msg.note] = tiempo_absoluto
            
        elif (msg.type == 'note_off') or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in notas_activas:
                inicio = notas_activas.pop(msg.note)
                duracion = tiempo_absoluto - inicio
                frecuencia = midi_a_hz(msg.note)
                
                # Ajuste de duración: restamos el silencio que inyectaremos después
                duracion_total = int(duracion * 2) 
                
                if duracion_total > (silencio_ms + 20):
                    nota_limpia = duracion_total - silencio_ms
                    # Añadimos la nota recortada
                    notas.append((frecuencia, nota_limpia))
                    # Añadimos el silencio obligatorio para separar
                    notas.append((0, silencio_ms))
                elif duracion_total > 20:
                    # Si es muy corta, no restamos silencio para no perderla
                    notas.append((frecuencia, duracion_total))
    
    return notas

archivo = "Undertale - Megalovania (No Bass).mid.mid"

# Extraemos (puedes ajustar el 30 si quieres más o menos separación)
melodia = extraer_melodia(archivo, pista_idx=0, silencio_ms=30) 


with open(archivo.replace(".mid", "_melodia.txt"), "w") as f:
    f.write(str(melodia))

print(f"Se extrajeron {len(melodia)} notas con separación aplicada.")