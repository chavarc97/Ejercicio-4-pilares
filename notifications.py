from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean
from typing import Protocol, List, Optional
import json
import re
import time
import os

# ==================== PROTOCOLO/INTERFAZ ====================


class Notificador(Protocol):
    def enviar(self, mensaje: str) -> None: ...

# ==================== IMPLEMENTACIones DE NOTIFICACIONES ====================


class NotificadorEmail:
    """Implementación concreta del protocolo Notificador (Encapsulación)"""

    def __init__(self, destinatario: str, servidor: str = "smtp.gmail.com") -> None:
        self._destinatario = destinatario  # Encapsulación
        self._servidor_smtp = servidor     # Encapsulación

    def enviar(self, mensaje: str) -> None:
        if self.validar_email():
            print(
                f"[EMAIL via {self._servidor_smtp} a {self._destinatario}] {mensaje}")
        else:
            print(f"[ERROR EMAIL] Dirección inválida: {self._destinatario}")

    def validar_email(self) -> bool:
        """Validación simple de email"""
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(patron, self._destinatario) is not None


class NotificadorWebhook:
    def __init__(self, url: str) -> None:
        self._url = url

    def enviar(self, mensaje: str) -> None:
        if self.validar_url():
            print(f"[WEBHOOK {self._url}] {mensaje}")
        else:
            print(f"[ERROR WEBHOOK] URL no valida")

    def validar_url(self) -> bool:
        """ Validación simple de la URL"""
        return self._url.startswith("http://", "https://")


class NotificadorSMS:
    """Nueva implementación del protocolo Notificador"""

    def __init__(self, numero: str, proveedor: str = "Twilio") -> None:
        self._numero = numero       # Encapsulación
        self._proveedor = proveedor  # Encapsulación

    def enviar(self, mensaje: str) -> None:
        numero_formateado = self.formato_numero()
        print(f"[SMS via {self._proveedor} a {numero_formateado}] {mensaje}")

    def formato_numero(self) -> str:
        """Formatea el número telefónico"""
        # Elimina caracteres no numéricos
        numeros = ''.join(filter(str.isdigit, self._numero))
        if len(numeros) >= 10:
            return f"+1-{numeros[-10:-7]}-{numeros[-7:-4]}-{numeros[-4:]}"
        return self._numero


# ==================== CLASES DE CONFIGURACIÓN Y REGISTRO ====================
@dataclass
class ConfiguracionSistema:
    intervalo_verificacion: int = 10  # Cada 10 segundos
    max_alertas_por_hora: int = 50
    nivel_log: str = "INFO"  # DEBUG, INFO, WARN, ERROR
    ruta_logs: str = "./logs/"

    def cargar_configuracion(self, archivo: str) -> None:
        """Carga configuración desde archivo"""
        print(f"Cargando configuración desde: {archivo}")

    def guardar_configuracion(self) -> None:
        """Guarda configuración actual"""
        print("Configuración guardada exitosamente")

    def validar_configuracion(self) -> bool:
        """Valida que la configuración sea correcta"""
        return (self.intervalo_verificacion > 0 and
                self.max_alertas_por_hora > 0 and
                self.nivel_log in ["DEBUG", "INFO", "WARNING", "ERROR"])


@dataclass
class RegistroAlerta:
    """Clase para registrar alertas del sistema"""
    sensor_id: str
    mensaje: str
    nivel: str
    valor_medido: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_json(self) -> str:
        """Convierte el registro a JSON"""
        return json.dumps({
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'mensaje': self.mensaje,
            'nivel': self.nivel,
            'valor_medido': self.valor_medido
        })

    def to_csv(self) -> str:
        """Convierte el registro a formato CSV"""
        return f"{self.timestamp},{self.sensor_id},{self.nivel},{self.valor_medido},'{self.mensaje}'"


# ==================== CLASES DE SENSOR (ABSTRACCIÓN) ====================
@dataclass
class Sensor(ABC):
    id: str
    ventana: int = 5
    ubicacion: str = "No especificada"
    _calibracion: float = field(default=0.0, repr=False)  # encapsulado
    _buffer: list[float] = field(default_factory=list, repr=False)

    def leer(self, valor: float) -> None:
        """Agrega lectura aplicando calibración y mantiene ventana móvil."""
        v = valor + self._calibracion
        self._buffer.append(v)
        if len(self._buffer) > self.ventana:
            self._buffer.pop(0)

    @property
    def promedio(self) -> float:
        return mean(self._buffer) if self._buffer else 0.0

    def obtener_estado(self) -> str:
        """Obtiene el estado actual del sensor"""
        estado = "ALERTA" if self.en_alerta() else "NORMAL"
        return f"Sensor {self.id} ({self.obtener_tipo()}): {estado} - Promedio: {self.promedio:.2f}"

    @abstractmethod
    def en_alerta(self) -> bool: ...

    @abstractmethod
    def obtener_tipo(self) -> str: ...


# ==================== SUBCLASES DE SENSORES (HERENCIA) ====================
@dataclass
class SensorTemperatura(Sensor):
    umbral_max: float = 80.0
    umbral_min: float = -10.0
    unidad: str = "C"

    def en_alerta(self) -> bool:
        """Polimorfismo: implementación específica para temperatura"""
        return self.promedio >= self.umbral_max or self.promedio <= self.umbral_min

    def obtener_tipo(self) -> str:
        """Implementación específica del método abstracto"""
        return f"Temperatura ({self.unidad})"

    def celsius_to_fahrenheit(self) -> float:
        """Convierte la temperatura actual a Fahrenheit"""
        return (self.promedio * 9/5) + 32


@dataclass
class SensorVibracion(Sensor):
    rms_umbral: float = 2.5
    frecuencia: int = 1000

    def en_alerta(self) -> bool:
        """Polimorfismo: implementación específica para vibración"""
        return abs(self.calcular_rms()) >= self.rms_umbral

    def obtener_tipo(self) -> str:
        """Implementación específica del método abstracto"""
        return f"Vibración @ {self.frecuencia}Hz"

    def calcular_rms(self) -> float:
        """Calcula el valor RMS aproximado"""
        if not self._buffer:
            return 0.0
        return (sum(x**2 for x in self._buffer) / len(self._buffer)) ** 0.5


# ADD: Sensor para humedad respetando la herencia y polimorfismo
@dataclass
class SensorHumedad(Sensor):
    umbral_humedad: float = 85.0
    tipo_ambiente: str = "interior"

    def en_alerta(self) -> bool:
        return self.promedio >= self.umbral_humedad

    def obtener_tipo(self) -> str:
        """Implementación específica del método abstracto"""
        return f"Humedad en {self.tipo_ambiente}"

    def calcular_punto_rocio(self) -> float:
        """Calcula el punto de rocío aproximado"""
        # Fórmula aproximada para punto de rocío
        if self.promedio > 0:
            return self.promedio - ((100 - self.promedio) / 5)
        return 0.0


# ==================== GESTOR DE ALERTAS (COMPOSICIÓN) ====================
class GestorAlertas:
    """Gestor central de alertas que utiliza Composición"""
    def __init__(self, configuracion: ConfiguracionSistema) -> None:
        self._sensores: List[Sensor] = []              # Composición
        self._notificadores: List[Notificador] = []    # Composición
        self._configuracion = configuracion            # Composición
        self._log_alertas: List[RegistroAlerta] = []   # Composición

    def agregar_sensor(self, sensor: Sensor) -> None:
        """Agrega un sensor al sistema"""
        self._sensores.append(sensor)
        print(f"✅ Sensor {sensor.id} agregado al sistema")

    def agregar_notificador(self, notificador: Notificador) -> None:
        """Agrega un notificador al sistema"""
        self._notificadores.append(notificador)
        print(f"✅ Notificador {type(notificador).__name__} agregado al sistema")

    def evaluar_y_notificar(self) -> None:
        """Evalúa todos los sensores y notifica si hay alertas"""
        alertas_encontradas = 0
        for sensor in self._sensores:
            if sensor.en_alerta():
                alertas_encontradas += 1
                mensaje = f"🚨 ALERTA: Sensor {sensor.id} en umbral (promedio={sensor.promedio:.2f})"
                
                # Crear registro de alerta
                registro = RegistroAlerta(
                    sensor_id=sensor.id,
                    mensaje=mensaje,
                    nivel="WARNING",
                    valor_medido=sensor.promedio
                )
                self._log_alertas.append(registro)
                
                # Notificar a todos los notificadores (Polimorfismo)
                for notificador in self._notificadores:
                    notificador.enviar(mensaje)
        
        if alertas_encontradas == 0:
            print("✅ No se detectaron alertas - Sistema funcionando normal")
        else:
            print(f"🚨 Se detectaron {alertas_encontradas} alertas")

    def generar_reporte(self) -> str:
        """Genera un reporte del estado del sistema"""
        reporte = "\n" + "="*60 + "\n"
        reporte += "📊 REPORTE COMPLETO DEL SISTEMA\n"
        reporte += "="*60 + "\n"
        reporte += f"📱 Sensores activos: {len(self._sensores)}\n"
        reporte += f"📢 Notificadores: {len(self._notificadores)}\n"
        reporte += f"🚨 Alertas registradas: {len(self._log_alertas)}\n\n"
        
        reporte += "📊 Estado detallado de sensores:\n"
        reporte += "-" * 60 + "\n"
        for sensor in self._sensores:
            reporte += f"  {sensor.obtener_estado()}\n"
            
        if self._log_alertas:
            reporte += "\n🚨 Últimas 5 alertas:\n"
            reporte += "-" * 60 + "\n"
            for registro in self._log_alertas[-5:]:
                reporte += f"  [{registro.timestamp.strftime('%H:%M:%S')}] {registro.sensor_id}: {registro.mensaje}\n"
                
        reporte += "="*60 + "\n"
        return reporte

    def limpiar_historico(self) -> None:
        """Limpia el histórico de alertas"""
        alertas_eliminadas = len(self._log_alertas)
        self._log_alertas.clear()
        print(f"🧹 Histórico limpiado: {alertas_eliminadas} alertas eliminadas")

    @property
    def sensores(self) -> List[Sensor]:
        """Getter para acceder a los sensores"""
        return self._sensores.copy()  # Devuelve copia para proteger la lista original


# ==================== PANEL DE CONTROL ====================
class PanelDeControl:
    """Clase para la interfaz de usuario del sistema"""
    def __init__(self, sistema: 'SistemaDeMonitoreo') -> None:
        self._sistema = sistema      # Asociación
        self._interfaz_activa = False
        
    def limpiar_pantalla(self) -> None:
        """Limpia la pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def mostrar_dashboard(self) -> None:
        """Muestra el dashboard principal"""
        if self._sistema:
            print("\n" + "="*60)
            print(f"  🖥️  PANEL DE CONTROL - {self._sistema._nombre}")
            print(f"  📦 Versión: {self._sistema._version}")
            print(f"  🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60)
            print(self._sistema.obtener_estado_general())
            
    def mostrar_menu_principal(self) -> None:
        """Muestra el menú principal"""
        print("\n" + "🎮 MENÚ PRINCIPAL".center(60, "="))
        print("1. 📊 Ver estado actual del sistema")
        print("2. 📈 Generar reporte completo") 
        print("3. 📝 Simular lecturas de sensores")
        print("4. 🔍 Evaluar y notificar alertas")
        print("5. ⚙️  Configurar sistema")
        print("6. 🧹 Limpiar histórico de alertas")
        print("7. 📱 Gestionar notificadores")
        print("8. 🌡️  Gestionar sensores")
        print("0. ❌ Salir del sistema")
        print("="*60)

    def procesar_comandos(self) -> bool:
        """Procesa comandos del usuario - Retorna False para salir"""
        try:
            comando = input("👉 Selecciona una opción: ").strip()
            
            if comando == "1":
                self.mostrar_estado_sistema()
            elif comando == "2":
                self.generar_reporte_completo()
            elif comando == "3":
                self.simular_lecturas()
            elif comando == "4":
                self.evaluar_alertas()
            elif comando == "5":
                self.configurar_sistema()
            elif comando == "6":
                self.limpiar_historico()
            elif comando == "7":
                self.gestionar_notificadores()
            elif comando == "8":
                self.gestionar_sensores()
            elif comando == "0":
                return False
            else:
                print("❌ Comando no reconocido. Intenta de nuevo.")
                
            input("\n⏸️  Presiona Enter para continuar...")
            return True
            
        except KeyboardInterrupt:
            print("\n\n👋 Saliendo del sistema...")
            return False
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return True

    def mostrar_estado_sistema(self) -> None:
        """Muestra el estado actual del sistema"""
        self.limpiar_pantalla()
        self.mostrar_dashboard()

    def generar_reporte_completo(self) -> None:
        """Genera y muestra el reporte completo"""
        print("📊 Generando reporte completo...")
        reporte = self._sistema.gestor_alertas.generar_reporte()
        print(reporte)

    def simular_lecturas(self) -> None:
        """Permite al usuario simular lecturas de sensores"""
        sensores = self._sistema.gestor_alertas.sensores
        if not sensores:
            print("❌ No hay sensores configurados en el sistema")
            return
            
        print("🎲 SIMULADOR DE LECTURAS DE SENSORES")
        print("="*50)
        
        for i, sensor in enumerate(sensores, 1):
            print(f"{i}. {sensor.id} ({sensor.obtener_tipo()}) - {sensor.ubicacion}")
            
        try:
            opcion = int(input("Selecciona sensor (número): ")) - 1
            if 0 <= opcion < len(sensores):
                sensor_seleccionado = sensores[opcion]
                valor = float(input(f"Ingresa valor para {sensor_seleccionado.id}: "))
                sensor_seleccionado.leer(valor)
                print(f"✅ Lectura {valor} agregada a {sensor_seleccionado.id}")
                print(f"📊 Promedio actual: {sensor_seleccionado.promedio:.2f}")
            else:
                print("❌ Opción inválida")
        except ValueError:
            print("❌ Valor inválido")

    def evaluar_alertas(self) -> None:
        """Evalúa sensores y muestra alertas"""
        print("🔍 Evaluando sensores y generando alertas...")
        print("="*50)
        self._sistema.gestor_alertas.evaluar_y_notificar()

    def configurar_sistema(self) -> None:
        """Muestra opciones de configuración"""
        print("⚙️  CONFIGURACIÓN DEL SISTEMA")
        print("="*40)
        config = self._sistema.gestor_alertas._configuracion
        print(f"📅 Intervalo de verificación: {config.intervalo_verificacion}s")
        print(f"📊 Máximo alertas por hora: {config.max_alertas_por_hora}")
        print(f"📝 Nivel de log: {config.nivel_log}")
        print(f"📁 Ruta de logs: {config.ruta_logs}")

    def limpiar_historico(self) -> None:
        """Limpia el histórico de alertas"""
        confirmacion = input("🧹 ¿Estás seguro de limpiar el histórico? (s/N): ")
        if confirmacion.lower() == 's':
            self._sistema.gestor_alertas.limpiar_historico()
        else:
            print("❌ Operación cancelada")

    def gestionar_notificadores(self) -> None:
        """Muestra información de notificadores"""
        print("📱 GESTIÓN DE NOTIFICADORES")
        print("="*40)
        notificadores = self._sistema.gestor_alertas._notificadores
        if notificadores:
            for i, notif in enumerate(notificadores, 1):
                print(f"{i}. {type(notif).__name__}")
        else:
            print("❌ No hay notificadores configurados")

    def gestionar_sensores(self) -> None:
        """Muestra información detallada de sensores"""
        print("🌡️  GESTIÓN DE SENSORES")
        print("="*40)
        sensores = self._sistema.gestor_alertas.sensores
        if sensores:
            for sensor in sensores:
                print(f"📊 {sensor.obtener_estado()}")
                if isinstance(sensor, SensorTemperatura):
                    print(f"    🌡️ Temperatura en Fahrenheit: {sensor.celsius_to_fahrenheit():.1f}°F")
                elif isinstance(sensor, SensorVibracion):
                    print(f"    📳 RMS actual: {sensor.calcular_rms():.2f}")
                elif isinstance(sensor, SensorHumedad):
                    print(f"    💧 Punto de rocío: {sensor.calcular_punto_rocio():.1f}%")
                print()
        else:
            print("❌ No hay sensores configurados")

    def actualizar_interfaz(self) -> None:
        """Actualiza la interfaz"""
        self._interfaz_activa = True
        self.limpiar_pantalla()
        self.mostrar_dashboard()


# ==================== SISTEMA PRINCIPAL (AGREGACIÓN) ====================
class SistemaDeMonitoreo:
    def __init__(self, nombre: str, version: str = "1.0.0") -> None:
        self._nombre = nombre                                      # Encapsulación
        self._version = version                                    # Encapsulación
        configuracion = ConfiguracionSistema()
        self._gestor_alertas = GestorAlertas(configuracion)       # Agregación
        self._panel_control = PanelDeControl(
            self)                  # Agregación

    def inicializar(self) -> None:
        """Inicializa el sistema completo"""
        print(f"Inicializando sistema {self._nombre} v{self._version}")
        self._panel_control.actualizar_interfaz()

    def detener(self) -> None:
        """Detiene el sistema"""
        print(f"Deteniendo sistema {self._nombre}")

    def obtener_estado_general(self) -> str:
        """Obtiene el estado general del sistema"""
        return self._gestor_alertas.generar_reporte()

    @property
    def gestor_alertas(self) -> GestorAlertas:
        """Propiedad para acceder al gestor de alertas"""
        return self._gestor_alertas

    @property
    def panel_control(self) -> PanelDeControl:
        """Propiedad para acceder al panel de control"""
        return self._panel_control


# ==================== FACTORY PATTERN ====================
class SensorFactory:
    """Factory para crear diferentes tipos de sensores (Dependencia)"""
    @staticmethod
    def crear_sensor_temperatura(id: str, umbral: float, ubicacion: str = "No especificada") -> SensorTemperatura:
        """Crea un sensor de temperatura"""
        return SensorTemperatura(id=id, umbral_max=umbral, ubicacion=ubicacion)

    @staticmethod
    def crear_sensor_vibracion(id: str, rms: float, ubicacion: str = "No especificada") -> SensorVibracion:
        """Crea un sensor de vibración"""
        return SensorVibracion(id=id, rms_umbral=rms, ubicacion=ubicacion)

    @staticmethod
    def crear_sensor_humedad(id: str, umbral: float, ubicacion: str = "No especificada") -> SensorHumedad:
        """Crea un sensor de humedad"""
        return SensorHumedad(id=id, umbral_humedad=umbral, ubicacion=ubicacion)


# =================== CONFIGURACION INICIAL ==============================
def configurar_sistema_inicial(sistema: SistemaDeMonitoreo) -> None:
    """Configura el sistema con datos de ejemplo"""
    print("⚙️  Configurando sistema inicial...")

    # Crear notificadores usando diferentes implementaciones (Polimorfismo)
    email_notif = NotificadorEmail("admin@empresa.com", "smtp.empresa.com")
    webhook_notif = NotificadorWebhook("https://api.empresa.com/alertas")
    sms_notif = NotificadorSMS("555-123-4567", "Twilio")

    # Agregar notificadores al sistema
    sistema.gestor_alertas.agregar_notificador(email_notif)
    sistema.gestor_alertas.agregar_notificador(webhook_notif)
    sistema.gestor_alertas.agregar_notificador(sms_notif)

    # Crear sensores usando Factory Pattern (Dependencia)
    factory = SensorFactory()
    temp_sensor = factory.crear_sensor_temperatura(
        "TEMP_001", 75.0, "Sala de servidores")
    vibra_sensor = factory.crear_sensor_vibracion(
        "VIB_001", 2.0, "Motor principal")
    humid_sensor = factory.crear_sensor_humedad("HUM_001", 80.0, "Almacén")

    # Agregar sensores al sistema
    sistema.gestor_alertas.agregar_sensor(temp_sensor)
    sistema.gestor_alertas.agregar_sensor(vibra_sensor)
    sistema.gestor_alertas.agregar_sensor(humid_sensor)

    # Agregar algunas lecturas de ejemplo
    print("📊 Agregando lecturas de ejemplo...")
    temp_sensor.leer(25.0)   # Normal
    temp_sensor.leer(30.0)   # Normal
    temp_sensor.leer(85.0)   # ¡Alerta!

    vibra_sensor.leer(1.0)   # Normal
    vibra_sensor.leer(1.5)   # Normal

    humid_sensor.leer(60.0)  # Normal
    humid_sensor.leer(70.0)  # Normal
    humid_sensor.leer(90.0)  # ¡Alerta!

    print("✅ Sistema configurado correctamente")


# ==================== EJEMPLO DE USO ====================
def main() -> None:
    """Función principal con menú interactivo"""
    print("🎮" + "="*58 + "🎮")
    print("🚀 SISTEMA DE MONITOREO INTELIGENTE - 4 PILARES OOP 🚀")
    print("🎮" + "="*58 + "🎮")

    # Crear sistema principal
    sistema = SistemaDeMonitoreo("MonitorPro", "1.0.0")

    # Configurar sistema inicial
    configurar_sistema_inicial(sistema)

    # Inicializar sistema
    sistema.inicializar()
    
    # Bucle principal del menú
    sistema_activo = True
    while sistema_activo:
        try:
            sistema.panel_control.mostrar_menu_principal()
            sistema_activo = sistema.panel_control.procesar_comandos()
        except KeyboardInterrupt:
            print("\n\n👋 Recibido Ctrl+C - Saliendo del sistema...")
            sistema_activo = False
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            print("🔄 Reiniciando menú...")
            time.sleep(2)
    
    # Detener sistema
    sistema.detener()
    print("👋 ¡Gracias por usar el Sistema de Monitoreo!")
    print("🎓 Demostración de los 4 Pilares OOP completada")


if __name__ == "__main__":
    main()
