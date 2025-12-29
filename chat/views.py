'''
Proyecto: CEAbot: asistente de ventas impulsado con inteligencia artificial
Descripcion: Este proyecto es un chatbot, capaz de hacer consultas de datos 
acerca de productos, detectar oportunidades de venta, capturar los datos del 
cliente y enviar un correo a un agente de ventas.

tecnologias aplicadas:
->Django
->OPenRouter API
->OpenAi
'''
#Librerias de Django para API
from rest_framework.views import APIView
from rest_framework.response import Response 
from django.conf import settings, traceback
#Libreria de OPENAI
from openai import OpenAI
#Expresiones regulares
import re 
#Envio de correos
import smtplib
from email.message import EmailMessage

import os
import random
import xmlrpc.client


class CeaBot_API(APIView):
    #Constructor 
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #Variables Globales
        #API KEYS
        self.apiKey1 = settings.API_KEY1
        self.apiKey2 = settings.API_KEY2
        self.apiKey3 = settings.API_KEY3
        self.apiKey4 = settings.API_KEY4
        #PARAMETROS OPENROUTER
        self.url = "https://openrouter.ai/api/v1"
        self.model = "meta-llama/llama-3.3-70b-instruct:free"
        self.messages = []
        self.mail = EmailMessage()
        #CREDENCIALES EMAIL
        self.myMail = settings.CEA_MAIL
        self.myPassword = settings.CEA_PASS
        self.destinationMail = settings.DEST_MAIL
        self.destinationMailMTY = settings.DEST_MAILMTY
        #PARAMETROS ODOO
        self.odooDB = settings.ODOO_DB
        self.odooUser = settings.ODOO_USER
        self.odooPass = settings.ODOO_PASSWORD
        self.odooURL = settings.ODOO_URL
        #Conexion con Odoo
        try:
            self.common = xmlrpc.client.ServerProxy(f'{self.odooURL}/xmlrpc/2/common')
            self.uid = self.common.authenticate(self.odooDB, self.odooUser, self.odooPass, {})
            self.models = xmlrpc.client.ServerProxy(f'{self.odooURL}/xmlrpc/object')
        except Exception as e:
            print(f'Error de conexion: {e}')
    
        #Mensajes de contextualizacion 
        self.messages = [{
    "role": "system",
    "content": """
Eres un chatbot de ventas llamado *CEA bot* y trabajas para la empresa
*CEA: Control y Elementos de Automatización*.

CEA se dedica a la venta de componentes para automatización industrial,
como sensores, relevadores, PLCs, fuentes de poder, cables industriales
y equipos de redes industriales.

Tu comportamiento debe ser profesional, claro y conciso.

Tus funciones principales son:
1. Ayudar al cliente a buscar productos por nombre o número de parte (SKU).
2. Dar formato a datos del cliente.
3. Resolver dudas técnicas relacionadas exclusivamente con automatización industrial y redes industriales.
"""
}]

        self.messages.append({
    "role": "system",
    "content": """
TAREA #1: BÚSQUEDA DE PRODUCTOS

Después de saludar y presentarte como *CEA bot*, solicita al cliente
el nombre del producto (en singular) o el número de parte (SKU).

⚠️ REGLA CRÍTICA:
Cuando detectes uno o más SKUs, debes responder ÚNICAMENTE
con el siguiente formato EXACTO, sin texto adicional, sin saludo
y sin explicaciones.

FORMATO OBLIGATORIO:
BUSCAR_PRODUCTO: sku1, sku2, sku3

- Si es un solo producto:
BUSCAR_PRODUCTO: 1883390

- Si son varios productos:
BUSCAR_PRODUCTO: 1883390, 2A000004, 129028
"""
})

        self.messages.append({
    "role": "system",
    "content": """
EJEMPLOS — TAREA #1

Entrada del cliente:
"SKU: 1883390"
"Busco el artículo 1883390"
"¿Tienes disponible el 1883390?"

Respuesta correcta del bot:
BUSCAR_PRODUCTO: 1883390
"""
})

        self.messages.append({
    "role": "system",
    "content": """
Entrada del cliente:
"SKU: 1883390, 2A000004"
"Busco los productos 129028, 2A000004 y 1883390"

Respuesta correcta del bot:
BUSCAR_PRODUCTO: 1883390, 2A000004
BUSCAR_PRODUCTO: 129028, 2A000004, 1883390
"""
})
        
        self.messages.append({
    "role": "system",
    "content": """
TAREA #2: CREACION DE FORMATO DE DATOS PARA COTIZACIÓN

Después de mostrar la información de los productos,
el sistema solicitará al cliente los siguientes datos:

1. Nombre completo
2. Correo electrónico
3. Número de teléfono
4. Ciudad de residencia
5. Producto(s) y cantidad

⚠️ Cuando detectes que el cliente está proporcionando estos datos,
debes responder ÚNICAMENTE con el siguiente bloque de texto,
respetando exactamente el formato y los nombres de los campos.
NO agregues comentarios, saludos ni explicaciones.
"""
})
        self.messages.append({
    "role": "system",
    "content": """
FORMATO OBLIGATORIO:

REGISTRO_CLIENTE:
Nombre: nombre_del_cliente
Correo Electronico: correo_del_cliente
Numero de telefono: numero_de_telefono
Ciudad de residencia: ciudad
Productos: [
SKU1: cantidad
SKU2: cantidad
]
"""
})

 
        self.messages.append({
    "role": "system",
    "content": """
EJEMPLO 1 DE RESPUESTA CORRECTA — TAREA #2

Si el cliente escribe los siguientes datos (Sin importar el orden):

"Me llamo Juan Perez, mi correo es juanperez@example.com, soy de saltillo 
y me llevo una unidad de cada producto y mi numero es 5551234567 "

REGISTRO_CLIENTE:
Nombre: Juan Pérez
Correo Electronico: juanperez@example.com
Numero de telefono: 5551234567
Ciudad de residencia: Saltillo
Productos: [
1694525: 1
1520369: 1
1681868: 1
]
"""
})
        self.messages.append({
    "role": "system",
    "content": """
TAREA #3: RESOLUCIÓN DE DUDAS TÉCNICAS

El cliente puede hacer preguntas técnicas relacionadas con:
- Automatización industrial
- Sensores y actuadores
- PLCs
- Redes industriales (Ethernet/IP, Profinet, RJ45, M12, etc.)

Ejemplos válidos:
- ¿Qué es la función Auto-crossing?
- ¿Qué significa que un cable M12 sea recto?
- ¿Qué es un conector RJ45?

⚠️ RESTRICCIÓN:
Si la pregunta NO está relacionada con automatización industrial
o redes industriales, debes rechazarla de forma educada
indicando que solo puedes responder dudas técnicas de ese ámbito.
"""
})

                
        #LLamadas a los metododos
        self.conect()#Establece el cliente de OPenAi
        

    def conect(self):#Openrouter necesita de la libreria de OpenAI para funcionar 
        randNum = random.randint(1,4)
        apiKey = ""
        if randNum == 1:
            apiKey = self.apiKey1
        elif randNum == 2:
            apiKey = self.apiKey2
        elif randNum == 3:
            apiKey = self.apiKey3
        elif randNum == 4:
            apiKey = self.apiKey4

        self.client = OpenAI(api_key= apiKey , base_url= self.url)
    
    def chat(self, messages):
        chat = self.client.chat.completions.create(
                model= self.model,
                messages= messages, #el diccionario "messages" contiene el historial de mensajes 
            )
            
        return chat.choices[0].message.content
    
    #Aqui se carga el archivo Json que contiene los datos del proyecto
    def loadData(self):
        filePath =  os.path.join(settings.BASE_DIR,'chat','pxc_data.json')
        try:
            with open(filePath,'r',encoding='utf-8') as f:
                self.productos = json.load(f)
        except FileNotFoundError:
            print(f"error al abrir el arhivo")
        except json.JSONDecodeError:
            print("El archivo no tiene un formato valido")
        except Exception as e:
            print(f"ha ocurrido un error {e}")
            
    """
    Este metodo hace consultas de BD en Odoo via XMLRPC y procesa una salida de 
    texto con los datos del producto o los prodictos consultados 
    """
    def buscarByOdoo(self, entrada):
        #Declaracion de variables
        resultados = ''
        promt = ''
        noEncontrados =''
        countFound = 0
        countNotFounded = 0
        arrnoEncontrados = []
        #Se utilizan regex para eliminar el bloque de texto 'BUSCAR_PRODUCTO'
        coinsidencia = re.findall(r"(?:BUSCAR_PRODUCTO|Producto|producto):\s*(.*)", entrada,re.IGNORECASE)
        
        print(f"[DEBUG] Consulta: {coinsidencia}")
        #Crear un arreglo con los SKU de los productos separados por ","
        cadenas = coinsidencia[0].replace(" ","").split(",")#Se eliminan los espacios
        #Se itera por cada elemento en el arreglo
        for cadena in cadenas:
            #Con expresiones regulares, se valida se la el elemento cumple con el patron de un SKU
            if re.fullmatch(r'^[.-]?[A-Z0-9]+([./-][A-Z0-9]+)*$', cadena.strip()): #Si la cadena filtrada es es un numero de 7 digitos, es un SKU de Parker Phoenix 
                #llamada a odoo con el elemento del arreglo
                producto = self.models.execute_kw(
                    self.odooDB,
                    self.uid,
                    self.odooPass,
                    'product.product',
                    'search_read',
                    [[('name', '=', cadena)]],
                    {'fields':[ 'name', 'default_code', 'list_price']}
                        )
                #Si el producto se encuentra, se agrega una variable un formularios con los elementos de este 
                if producto:
                    resultados += f"\nNumero de Parte: {producto[0]['name']}\nDescripcion: {producto[0]['default_code']}\nPrecio por Unidad: {producto[0]['list_price']}\n"
                    countFound += 1 
                else:
                    #Si no se encuentra se guarda el termino y se suma un contador 
                    countNotFounded += 1
                    arrnoEncontrados.append(cadena)
                    
            else:
                promt= f"""\n{cadena} no cumple con los requisitos necesarios para ser considerado un numero de parte."""
                
        if arrnoEncontrados:#Se crea una lista en texto con los productos no encontrados
            for i, prod in enumerate(arrnoEncontrados):
                        if i == len(arrnoEncontrados) -1:
                            noEncontrados += prod.strip() + "."
                        else:
                            noEncontrados += prod.strip() + ", "
        if resultados:#Si hay resultados se crea un texto final y este varia..
            #Dependiendo si solo se encontro un producto o mas, se utilizan plurales
            if  countFound == 1:
                promt += "Este es el producto que podrias estar buscando:\n" + resultados
                promt += f"""\npor favor, si estas interesado en este producto, """
            else:
                promt += "Estos son los productos que podrias estar buscando:\n" + resultados
                promt += f"""\npor favor, si estas interesado en alguno de estos productos, """
            promt += f"""proporcioname los siguientes datos:

✅ Nombre Completo

✅ Numero de telefono

✅ Correo Electronico

✅ Ciudad de residencia

✅ Numero de parte del producto(s)"""
        else:#Del mismo modo, se crea un texto fiunal para los productos no encontrados
            promt += f"""No se encontraron en la base de datos productos que coinsidan con tu busqueda, por favor, 
se mas especifico o proporcioname el SKU del producto."""
        if noEncontrados:
            if countNotFounded == 1:
                promt += f"\n\nEl siguiente termino no fue encontrado en la base de datos: {noEncontrados}"
            else:
                promt += f"\n\nLos siguientes terminos no fueron encontrados en la base de datos: {noEncontrados}"
        return promt


    #Este metodo toma los datos del cliente, redacta un correo para un agente de ventas y lo envia 
    def registrarCliente(self, entrada):
        #Declaracion de variables 
        msj = ""
        destination = self.destinationMail
        subject = "NUEVO LEAD DE VENTA CAPTURADO"
        cadena = re.findall(r"(?:REGISTRO_CLIENTE):\s*(.*)", entrada, re.DOTALL) #Se elimina el bloque contienen los datos
        #Contiene el contenido del correo y se le añade la informacion
        content = f"""Hola Francisco,
Se ha registrado una nueva oportunidad de venta en el portal oficial de CEA, a continuacion te 
comparto los datos para que puedas darle seguimiento. 

{cadena[0]}

Saludos,
CEA bot 
Asistente de ventas 
CEA: control y elementos de Automatizacion
"""     
        #Configuracion de correos de destino 
        #Se captura la ciudad de residencia del cliente con una Regex
        firstMatch = re.search(r"Ciudad de residencia:\s*(.+)", entrada, re.IGNORECASE) 
        if firstMatch:
            print(f"DEBUG[Ciudad de residencia: {firstMatch.group(1)}]")
            #Si esta cadena extraida coincide con MTY o Monterrey, se asigna su mail correspondiente
            if re.search(r"\b(monterrey|mty)\b", firstMatch.group(1), re.IGNORECASE):
                destination = self.destinationMailMTY
        
        #Se llenan los parametros para el envio del MAIL        
        self.mail['Subject'] = subject
        self.mail['From'] = self.myMail
        self.mail['To'] = destination

        self.mail.set_content(content)
        #se envia el correo 
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
                smtp.login(self.myMail, self.myPassword)
                smtp.send_message(self.mail)
                print(f"DEBUG[Se envio un correo a {destination}]")
                #Mensaje de confirmacion para el usuario
                msj = f"""¡Gracias por contactarnos!

Hemos recibido correctamente tus datos de contacto y la solicitud de cotización para los productos de tu interés.
Un agente de CEA: Control y Elementos de Automatización se pondrá en contacto contigo lo antes posible para brindarte la información detallada y ayudarte con tu cotización.

Si tienes alguna duda o deseas agregar más información, no dudes en responder este mensaje.

¡Estamos para ayudarte!
CEA – Control y Elementos de Automatización"""
        #Si ocurrio un error con el correo se captura la excepcion
        # y se redacta un mensaje para el usuario       
        except Exception as e:
            print(f"Error al enviar el correo {e}")
            msj = f"""¡Algo salió mal!

Lamentablemente, no pudimos registrar tus datos de contacto ni tu solicitud de cotización en nuestro sistema.
Por favor, verifica la información ingresada e intenta nuevamente.

Si el problema persiste, puedes contactarnos directamente a través de nuestros canales de atención para recibir asistencia.

CEA – Control y Elementos de Automatización
Comprometidos con brindarte el mejor servicio.

"""
        return msj
    #Metodo post para la API que resive el mensaje del usuario devuelve la respuesta del modelos
    def post(self, request):
        #se rescive el historial de mensajes, ya que esta se debe almacenar desde
        #la aplicacion front
        history = request.data.get("messages",[])
        #Se resive el mensaje del usuario
        user_message = request.data.get("message")
        #Si el mensaje no es resivido el API responde con un mensaje de error
        if not user_message:
            return Response({"error":"No se recivio un mensaje de parte del usuario"}, status = 400)
        #Se añade el historial de mensajes de la app front al de la API
        self.messages.extend(history)
        
        try:
            #Se llama al metodo chat y se pasa como parametro el historial de mensajes Global
            response = self.chat(self.messages)
            response_text = ""
            #Si la REGEX coinside con el bloque de texto de consulta de datos se hace la llamada 
            #al metofo buscarProducto, la respuesta se pasa como respuesta del chatbot
            if re.search("(BUSCAR_PRODUCTO|Producto|producto):.*", response ):
                response_text = self.buscarByOdoo(response)
            #De la misma forma, si la REGUEX captura el bloque con los datos del cliente,
            #se llama al metodo registrarCliente el resultado se devuelve como respuesta
            elif re.search("(REGISTRO_CLIENTE):.*",response):
                response_text = self.registrarCliente(response)
                
                
            else:
                response_text = response #en caso de que no sea ninguna de las dos, se pasa la respuesta del modelo

            return Response({"response": response_text}, status=200)
            
        except Exception as e:
            print("ERROR en respuesta de API:")
            traceback.print_exc() #
            return Response({"error": str(e)}, status=500)

