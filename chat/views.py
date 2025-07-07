
from rest_framework.views import APIView
from rest_framework.response import Response 
from openai import OpenAI
import re 
import json
import smtplib
from email.message import EmailMessage
from django.conf import settings
import os
import random

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

class CeaBot_API(APIView):
    #Constructor 
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #Variables Globales
        self.apiKey1 = settings.API_KEY1
        self.apiKey2 = settings.API_KEY2
        self.apiKey3 = settings.API_KEY3
        self.url = "https://openrouter.ai/api/v1"
        self.model = "meta-llama/llama-3.3-70b-instruct:free"
        self.messages = []
        self.mail = EmailMessage()
        self.myMail = settings.CEA_MAIL
        self.myPassword = settings.CEA_PASS
        self.destinationMail = settings.DEST_MAIL
        self.productos = {} 
        #Mensajes de contextualizacion 
        self.messages = [ {"role": "system", "content": f"""
Eres un chatbot de ventas llamado *CEA bot*, que trabaja para la empresa *CEA: Control y Elementos de Automatización*.

CEA se dedica a la venta de herramientas y componentes para automatización industtrial, incluyendo sensores, relevadores, PLCs, fuentes de poder, entre otros.

Tu función es:

1. Proporcionar información sobre productos que el cliente está buscando (nombre o Numero de parte).
2. Capturar numbre, numero de telefono y correo del cliente 
3. Resolver dudas al cliente sobre temas de automatizacion industrial y redes


"""}]
        self.messages.append({"role": "system", "content": f"""
Para cumplir la TAREA #1 (buscar productos):

Después de un saludo y presentarte como CEA bot, pide al cliente el nombre del producto (en singular) o el número de SKU.

Luego, responde **ÚNICAMENTE** con uno de los siguientes formatos exactos, sin agregar explicaciones ni texto adicional:

- Si el cliente menciona un producto:  
  BUSCAR_PRODUCTO: nombre_del_producto_en_singular
  (Ejemplo: BUSCAR_PRODUCTO: abrazadera final)

- Si el cliente menciona un SKU:  
  BUSCAR_PRODUCTO: número_de_parte
  (Ejemplo: BUSCAR_PRODUCTO: 1883390)
"""})

        self.messages.append({"role": "system", "content": f"""
Ejemplo 1 (por nombre de producto):
Si el cliente dice:  
"Busco una abrazadera final",  
"Tienes abrazaderas finales?",  
"Busca en tu base de datos abrazaderas finales"  

Tú debes responder:
BUSCAR_PRODUCTO: abrazadera final (nombre del producto en singular)
(Recuerda: usa siempre el nombre del producto en SINGULAR)
"""})

        self.messages.append({"role": "system", "content": f"""
Ejemplo 2 (por Numero de Parte):
Si el cliente dice:  
"SKU: 1883390",  
"Busco el artículo 1883390",  
"¿Tienes disponible el 1883390?"  

Tú debes responder:
BUSCAR_PRODUCTO: 1883390
"""})
        self.messages.append({"role":"assistant", "content":f"""
Para la TAREA #2: captura de datos del cliente.

Despues de mostrar los productos consultados, es posible que el cliente desee hacer una cotizacion de los productos.
Para ello, siempre despues de cada consulta, el sistema imprime en pantalla una solicitud para que el cliente ingrese los siguientes 
datos:

1. Nombre Completo
2. Correo Electronico
3. numero de telefono 
4. Ciudad de Residencia
5. SKU o numero de parte del producto (o productos)                                                         

Por lo que una vez que hayas detectado que el cliente esta ingresando estos datos tu UNICAMENTE deberas 
responder con el siguiente bloque de texto:
                                                           
REGISTRO_CLIENTE:

Nombre: nombre_del_cliente
Correo Electronico: correo_del_cliente
Numero de telefono: numero_de_telefono_del_cliente
Ciudad de residencia: ciudad_de_residencia 
Productos: [
Producto1: numero_de_unidades
producto2: numero_de:unidades                                 
]
"""})
 
        self.messages.append({"role":"system", "content":f"""✅ Ejemplo de respuesta correcta:
*Cliente:
Mi nombre es juan perez, mi correo es juanperez@example.com, mi numero de telefono: 555-123-4567
mi ciudad es Saltillo y los productos son 1694525, 1520369, 1681868
                     
REGISTRO_CLIENTE:
Nombre: Juan Pérez  
Correo Electronico: juanperez@example.com  
Numero de telefono: 555-123-4567
Ciudad de residencia:  Saltillo
productos: [
1694525,
1520369,
1681868
]  
"""})
        self.messages.append({"role":"system", "content":f"""PARA LA TAREA # 3: Resolver dudas sobre redes y automatizacion industrial
En base a la consulta de productos, se deplegaran en la pantalla del clinte, la informacion 
de dichos productos, es posible que el cliente tenga dudas subre esta informacion, asi que como ultima tarea,
tu deber es detectar las dudas del cliente y resolver estas dudas.

EJEMPLOS DE DUDAS:

¿Que es la funcion Autocrossing?
¿Que significa que un cable M12 sea recto?
¿Que significa Rj45?

Cabe destacar que si estas dudas no son del campo de la automatizacion industrial y redes
no puedes responder 

"""})
        
        #LLamadas a los metododos
        self.loadData()#Carga el archivo JSon de los productos
        self.conect()#Establece el cliente de OPenAi
        

    def conect(self):#Openrouter necesita de la libreria de OpenAI para funcionar 
        randNum = random.randint(1,3)
        if randNum == 1:
            apiKey = self.apiKey1
        elif randNum == 2:
            apiKey = self.apiKey2
        elif randNum == 3:
            apiKey = self.apiKey3

        self.client = OpenAI(api_key= apiKey ,
                             base_url= self.url)
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
            
    # Metodo que hace las consultas dentro del JSON 
    def buscarProducto(self, entrada):
        #Se elimina el bloque de texto que encapsula los terminos clave 
        coinsidencia = re.findall(r"(?:BUSCAR_PRODUCTO|Producto|producto):\s*(.*)", entrada,re.IGNORECASE)
        consulta = []
        if not coinsidencia:#Debug en consola en caso de que no se haya encontrado ese bloque de texto
            print("[DEBUG] No se encontro una solicitud de productos en la base de datos")
        
        cadena = coinsidencia[0]#Se inicializa la variable con los terminos clave
        #Si la cadena es una secuencia de 7 digitos (Correspondientes a SKU) entonces se pasa como esta
        if re.fullmatch(r'\b\d{7}\b', cadena.strip()):
            consulta = [cadena.strip()]
        else:
             #Por lo contrario si no es un SKU, entonces es una palabra clave o una
            consulta = [prod.strip().lower() for prod in cadena.split(',') if prod.strip()]
        #Debug para indicar que la consulta entro con exito
        print(f"[DEBUG] Consulta: {consulta}")
        resultados = []
        encontrados = set()
        #Se recorre el archivo de texto y se buscan coinsidencias
        for sku, datos in self.productos.items():
            descripcion = datos.get("descripcion","")
            for elemento in consulta:
                #Si el termino clave esta en la descripcion del producto o si es igual al SKU del mismo
                #Se llena un arreglo con los resultados que servira para redactar un mensaje para el usuario
                if re.search(elemento, descripcion.lower()) or elemento == sku: 
                    resultados.append(f"SKU: {sku}\nDescripcion: {descripcion}\n")
                    encontrados.add(elemento)
        #Si hubo termino que no se encpontro en la consulta se guarda en este arreglo 
        noEncontrados = [term for term in consulta if term not in encontrados]
        promt = ""
        #Se comienza a redactar un mensaje para el usuario con los resultados
        if resultados:
            promt += "Estos son los productos que podrias estar buscando:\n\n" + "\n".join(resultados)
            promt += f"""\npor favor, si estas interesado en alguno de estos productos, proporcioname los siguientes datos:

✅ Nombre Completo

✅ Numero de telefono

✅ Correo Electronico

✅ Ciudad de residencia

✅ Numero de parte del producto(s)"""
        else:
            promt += f"""No se encontraron en la base de datos productos que coinsidan con tu busqueda, por favor, 
se mas especifico o proporcioname el SKU del producto."""
       
        if noEncontrados:
            promt+= "\nlos siguientes terminos no fueron encontrados en la base de datos:"

            for elemento in noEncontrados:
                promt += f"{elemento}, "
        

        return promt
    #Este metodo toma los datos del cliente, redacta un correo para un agente de ventas y lo envia 
    def registrarCliente(self, entrada):
        msj = ""
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
"""     #se configuran los correos de envio y destinatario
        self.mail['Subject'] = subject
        self.mail['From'] = self.myMail
        self.mail['To'] = self.destinationMail

        self.mail.set_content(content)
        #se envia el correo 
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
                smtp.login(self.myMail, self.myPassword)
                smtp.send_message(self.mail)
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
                response_text = self.buscarProducto(response)
            #De la misma forma, si la REGUEX captura el bloque con los datos del cliente,
            #se llama al metodo registrarCliente el resultado se devuelve como respuesta
            elif re.search("(REGISTRO_CLIENTE):.*",response):
                response_text = self.registrarCliente(response)
                
    
            else:
                response_text = response #en caso de que no sea ninguna de las dos, se pasa la respuesta del modelo
           
            return Response({"response": response_text}, status=200)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)    
        

# Create your views here.
