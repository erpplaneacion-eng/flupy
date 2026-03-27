"""
Modelos de base de datos local (SQLite) usando Peewee ORM.
Representan las tablas que se almacenan en el dispositivo del supervisor.
"""
import uuid
import json
from datetime import datetime
from peewee import (
    SqliteDatabase, Model, CharField, TextField,
    DateTimeField, BooleanField, ForeignKeyField,
    IntegerField, AutoField
)

# Base de datos SQLite local — se crea en la carpeta de la app
db = SqliteDatabase("supervi.db", pragmas={"foreign_keys": 1})


def generar_id():
    """Genera un UUID único para identificar registros en sincronización."""
    return str(uuid.uuid4())


class ModeloBase(Model):
    """Clase base con campos comunes a todos los modelos."""
    id = AutoField()
    sync_id = CharField(default=generar_id, unique=True)  # UUID para sync con servidor
    creado_en = DateTimeField(default=datetime.now)
    actualizado_en = DateTimeField(default=datetime.now)
    sincronizado = BooleanField(default=False)  # False = pendiente de sync

    def save(self, *args, **kwargs):
        self.actualizado_en = datetime.now()
        return super().save(*args, **kwargs)

    class Meta:
        database = db


class Supervisor(ModeloBase):
    """
    Supervisor de campo del PAE.
    Se crea localmente al hacer login por primera vez.
    """
    nombre = CharField()
    email = CharField(unique=True)
    cedula = CharField(unique=True)
    zona = CharField(default="")        # Zona geográfica asignada
    token_jwt = TextField(default="")   # Token guardado para no hacer login cada vez

    def __str__(self):
        return f"{self.nombre} ({self.cedula})"

    class Meta:
        table_name = "supervisores"


class Comedor(ModeloBase):
    """
    Comedor escolar del programa PAE.
    La lista de comedores asignados viene del servidor.
    """
    nombre = CharField()
    municipio = CharField()
    institucion = CharField()        # Institución educativa donde está el comedor
    direccion = CharField(default="")
    activo = BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} — {self.municipio}"

    class Meta:
        table_name = "comedores"


class Visita(ModeloBase):
    """
    Visita de supervisión realizada por el supervisor a un comedor.
    Se crea en el dispositivo y se sincroniza al servidor.
    """
    ESTADOS = (
        ("borrador", "Borrador"),
        ("completada", "Completada"),
    )

    supervisor = ForeignKeyField(Supervisor, backref="visitas", on_delete="CASCADE")
    comedor = ForeignKeyField(Comedor, backref="visitas", on_delete="CASCADE")
    fecha = DateTimeField(default=datetime.now)
    estado = CharField(default="borrador", choices=ESTADOS)
    observaciones_generales = TextField(default="")

    def __str__(self):
        return f"Visita {self.comedor} — {self.fecha.strftime('%d/%m/%Y')}"

    class Meta:
        table_name = "visitas"


class ItemChecklist(ModeloBase):
    """
    Ítem individual del checklist de calidad e inocuidad.
    Cada visita tiene múltiples ítems agrupados por categoría.
    """
    CATEGORIAS = (
        ("instalaciones", "Instalaciones"),
        ("manipuladores", "Manipuladores de Alimentos"),
        ("alimentos", "Almacenamiento de Alimentos"),
        ("utensilios", "Utensilios y Equipos"),
        ("proceso", "Proceso de Preparación"),
    )

    RESPUESTAS = (
        ("SI", "Sí cumple"),
        ("NO", "No cumple"),
        ("NA", "No aplica"),
    )

    visita = ForeignKeyField(Visita, backref="checklist", on_delete="CASCADE")
    categoria = CharField(choices=CATEGORIAS)
    pregunta = TextField()
    respuesta = CharField(choices=RESPUESTAS, null=True)
    observacion = TextField(default="")
    orden = IntegerField(default=0)  # Orden de aparición en el checklist

    class Meta:
        table_name = "checklist_items"


class ColaSyncronizacion(Model):
    """
    Cola de operaciones pendientes de enviar al servidor.
    Cada vez que se crea/edita un registro, se agrega aquí.
    Al recuperar conexión se envía todo al servidor.
    """
    tabla = CharField()                     # Nombre de la tabla: visitas, checklist_items
    operacion = CharField()                 # INSERT, UPDATE, DELETE
    record_sync_id = CharField()            # sync_id del registro afectado
    datos = TextField()                     # JSON con los datos del registro
    timestamp = IntegerField()              # Unix timestamp de la operación
    enviado = BooleanField(default=False)   # True cuando el servidor lo confirmó

    class Meta:
        database = db
        table_name = "cola_sync"


def inicializar_db():
    """Crea las tablas si no existen. Llamar al iniciar la app."""
    db.connect(reuse_if_open=True)
    db.create_tables([
        Supervisor, Comedor, Visita, ItemChecklist, ColaSyncronizacion
    ], safe=True)


def agregar_a_cola_sync(tabla: str, operacion: str, record_sync_id: str, datos: dict):
    """
    Registra una operación en la cola de sincronización.
    Llamar después de cada INSERT o UPDATE en tablas principales.
    """
    import time
    ColaSyncronizacion.create(
        tabla=tabla,
        operacion=operacion,
        record_sync_id=record_sync_id,
        datos=json.dumps(datos, default=str),
        timestamp=int(time.time()),
        enviado=False,
    )
