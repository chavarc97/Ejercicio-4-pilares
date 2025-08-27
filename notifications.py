from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from statistics import mean
from typing import Protocol, List


class Notificador(Protocol):
    def enviar(self, mensaje: str) -> None: ...


class NotificadorEmail:
    def __init__(self, destinatario: str) -> None:
        self._destinatario = destinatario  # encapsulado

    def enviar(self, mensaje: str) -> None:
        print(f"[EMAIL a {self._destinatario}] {mensaje}")


class NotificadorWebhook:
    def __init__(self, url: str) -> None:
        self._url = url

    def enviar(self, mensaje: str) -> None:
        print(f"[WEBHOOK {self._url}] {mensaje}")


@dataclass
class Sensor(ABC):
    id: str
    ventana: int = 5
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
    
    @abstractmethod
    def en_alerta(self) -> bool: ...
    
@dataclass
class SensorTemperatura(Sensor):
    umbral: float = 80.0

    def en_alerta(self) -> bool:
        # Polimorfismo: cada sensor define su propia condición
        return self.promedio >= self.umbral

@dataclass
class SensorVibracion(Sensor):
    rms_umbral: float = 2.5

    def en_alerta(self) -> bool:
        # Ejemplo tonto de RMS -> promedio absoluto
        return abs(self.promedio) >= self.rms_umbral
    
class GestorAlertas:
    def __init__(self, sensores: List[Sensor], notificadores: List[Notificador]) -> None:
        self._sensores = sensores
        self._notificadores = notificadores

    def evaluar_y_notificar(self) -> None:
        for s in self._sensores:
            if s.en_alerta():
                msg = f"ALERTA: Sensor {s.id} en umbral (avg={s.promedio:.2f})"
                for n in self._notificadores:
                    n.enviar(msg)