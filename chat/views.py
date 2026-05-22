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
from itertools import product
from rest_framework.views import APIView
from rest_framework.response import Response 
from django.conf import settings, traceback
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
#Libreria de OPENAI
from openai import OpenAI
#Expresiones regulares
import re 
#Envio de correos
import smtplib
from email.message import EmailMessage
#Conversion de divisas en tiempo real
from currency_converter import CurrencyConverter
from datetime import datetime
import os
import random
import xmlrpc.client

@method_decorator(csrf_exempt, name='dispatch')
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
        self.model = "arcee-ai/trinity-large-thinking:free"
        self.messages = []
        self.mail = EmailMessage()
        #CREDENCIALES EMAIL
        self.myMail = settings.CEA_MAIL
        self.myPassword = settings.CEA_PASS
        self.destinationMail = settings.DEST_MAIL
        self.destinationMailMTY = settings.DEST_MAILMTY
        self.destinationMailSaltillo = settings.DEST_MAILSALTILLO
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
        #Para calculo de precios y conversion de divisas
        self.arrPriceDict = []
        #Mensaje de confirmacion
        self.confirmMsj = """¡Gracias por contactarnos! 🙌

Hemos recibido correctamente tus datos y tu solicitud de cotización para los productos de tu interés 🧾⚙️.

Un agente de CEA: Control y Elementos de Automatización se pondrá en contacto contigo a la brevedad para brindarte información detallada y ayudarte con tu cotización 📞💬.

Si tienes alguna duda o deseas agregar más información, no dudes en responder a este mensaje ✍️.

¡Será un gusto atenderte! 🤝
CEA – Control y Elementos de Automatización"""
        #Mensajes de contextualizacion 
        self.messages = [{
  "role": "system",
  "content": """
Eres *CEA bot*, un chatbot de ventas profesional que trabaja para la empresa
*CEA: Control y Elementos de Automatización*.

CEA se dedica a la comercialización de componentes de automatización industrial,
incluyendo sensores, PLCs, relevadores, fuentes de poder, cables industriales
y equipos de redes industriales.

Tu comunicación debe ser:
- Profesional
- Clara
- Breve
- Precisa

Tu objetivo es ayudar al cliente a:
1) Buscar productos por nombre o número de parte (SKU).
2) Resolver dudas técnicas relacionadas exclusivamente con automatización
   industrial y redes industriales.
"""
}]

        self.messages.append({
  "role": "system",
  "content": """
TAREA #1: BÚSQUEDA DE PRODUCTOS

1) Siempre saluda brevemente y preséntate como *CEA bot*.
2) Solicita al cliente el nombre del producto (en singular) o el SKU.

⚠️ REGLA CRÍTICA:
Si detectas uno o más SKUs en el mensaje del cliente, debes responder
ÚNICAMENTE con el siguiente formato EXACTO:

BUSCAR_PRODUCTO: sku1, sku2, sku3

❌ No agregues saludo
❌ No agregues explicaciones
❌ No agregues texto adicional
❌ No hagas preguntas

Ejemplos:
- Un solo SKU:
BUSCAR_PRODUCTO: 1883390

- Varios SKUs:
BUSCAR_PRODUCTO: 1883390, 2A000004, 129028
"""
})

        self.messages.append({
  "role": "system",
  "content": """
EJEMPLOS — TAREA #1

Entrada:
"SKU: .31BFDSR01.5"
"Busco el artículo .31BFDSR01.5"
"¿Tienes disponible el .31BFDSR01.5?"

Salida correcta:
BUSCAR_PRODUCTO: .31BFDSR01.5
"""
})

        self.messages.append({
  "role": "system",
  "content": """
Entrada:
"SKU: 1883390, 2A000004"
"Busco los productos 129028, 2A000004 y 1883390"

Salida correcta:
BUSCAR_PRODUCTO: 1883390, 2A000004
BUSCAR_PRODUCTO: 129028, 2A000004, 1883390
"""
})
        
        
        
        self.messages.append({
  "role": "system",
  "content": """
TAREA #2: RESOLUCIÓN DE DUDAS TÉCNICAS

Puedes responder únicamente preguntas relacionadas con:

- Automatización industrial
- PLCs
- Sensores y actuadores
- Redes industriales (Ethernet/IP, Profinet, Modbus, RJ45, M12, etc.)

Ejemplos válidos:
- ¿Qué es Profinet?
- ¿Qué significa que un cable M12 sea recto?
- ¿Qué es un conector RJ45 industrial?
- ¿Qué función cumple un PLC?

⚠️ RESTRICCIÓN:
Si la pregunta NO está relacionada con automatización industrial
o redes industriales, debes rechazarla de forma educada indicando que
solo puedes atender consultas técnicas de ese ámbito.
"""
})

    #Openrouter necesita de la libreria de OpenAI para funcionar        
    def chat(self, messages):
        
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
        
        allAPIS = [self.apiKey1,self.apiKey2,self.apiKey3,self.apiKey4]
        notSelectedApis = [api for api in allAPIS if api != apiKey]
        
        for i, api in enumerate(notSelectedApis):
            
            try:
                self.client = OpenAI(api_key= apiKey , base_url= self.url)
                chat = self.client.chat.completions.create(
                    model= self.model,
                    messages= messages, #el diccionario "messages" contiene el historial de mensajes 
                    )
                
                if not chat:
                    print("ERROR Respuesta vacia de openRouter")
                    return {
                        'content': 'Lo siento, ha habido un problema en al procesar tu mensaje.',
                        'action':'none'
                    }
                content = chat.choices[0].message.content
        
                if not content:
                    print("ERROR el contenido de la respuesta esta vacio")
                    apiKey = api
                    if i > len(notSelectedApis) -1:
                        continue
                    
                    return{
                        'content':'Lo siento, ha habido un problema al precesar tu mensaje.',
                        'action': 'none'
                    }    
                
                return {
                    'content': content,
                    'action':'none'
                }
            
            except AttributeError as e:
                print(f"ERROR AtributeError")
                print(f"Objeto chat {chat}")
                apiKey = api
                if i > len(notSelectedApis) -1:
                    continue
                return {
                    'content':'Lo siento, ha habido un error al prcesar tu mensaje.',
                    'action':'none'
                }
            except Exception as e:
                print(f"Error deconocido: {e}")
                apiKey = api
                if i > len(notSelectedApis) -1:
                    continue
                return {'content':'Lo siento, ha habido un problema al conectarme con la base de datos.',
                        'action':'none'}
    
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
        arrEncontrados = []
        action = "none"
        arrnoEncontrados = []
        arrNoExistencias = []
        provedoresIDs = [266,279,285,223,235,241,247] 
        #Se utilizan regex para eliminar el bloque de texto 'BUSCAR_PRODUCTO'
        coinsidencia = re.findall(r"(?:BUSCAR_PRODUCTO|Producto|producto):\s*(.*)", entrada,re.IGNORECASE)
        
        print(f"[DEBUG] Consulta: {coinsidencia}")
        #Crear un arreglo con los SKU de los productos separados por ","
        cadenas = coinsidencia[0].replace(" ","").split(",")#Se eliminan los espacios
        #Se itera por cada elemento en el arreglo
        for cadena in cadenas:
            stockCEA = 0
            stockProvedor = 0
            #Con expresiones regulares, se valida se la el elemento cumple con el patron de un SKU
            if re.fullmatch(r'^[.-]?[a-zA-Z0-9]+([./-][a-zA-Z0-9]+)*$', cadena.strip()): #Si la cadena filtrada es es un numero de 7 digitos, es un SKU de Parker Phoenix 
                #llamada a odoo con el elemento del arreglo
                producto = self.models.execute_kw(
                    self.odooDB,
                    self.uid,
                    self.odooPass,
                    'product.product',
                    'search_read',
                    [[('name', '=', cadena)]],
                    {'fields':[ 'id','name', 'default_code', 'list_price', 'x_studio_moneda','qty_available', 'x_studio_marca_1' ]}
                        )
                #Si el producto se encuentra, se agrega una variable un formularios con los elementos de este 
                if producto:
                    #:w
                    # self.arrPriceDict.append({"name":producto[0]['name'],"precio":producto[0]['listPrice'], "divisa":producto[0]['x_studio_moneda']})
                    #Busqueda de almacen
                    quants = self.models.execute_kw(
                        self.odooDB,
                        self.uid,
                        self.odooPass,
                        'stock.quant',
                        'search_read',
                        [[['product_id.name', '=', cadena]]],
                        {'fields':['id', 'location_id', 'quantity', 'reserved_quantity']}
                    )
                    
                    arrEncontrados.append(producto[0]['name'])
                    action = 'form'
                    resultados += f"\n🔢 Número de Parte: {producto[0]['name']}\n📝 Descripción:\n{producto[0]['default_code']}\n®️ Marca: {producto[0]['x_studio_marca_1']}"
                    if(producto[0]['list_price'] > 0 and producto[0]['x_studio_moneda'] != False):
                        resultados += f"\n💲 Precio por Unidad: {producto[0]['list_price']} {producto[0]['x_studio_moneda']} (IVA no incluido)"
                        
                    else:
                        resultados += "\n 💲 Precio por Unidad: ⚠️El precio de este producto actualmente esta descontinuado"
                        
                    countFound += 1
                    if producto[0]['qty_available'] > 0:
                        resultados += f"\n🧮Unidades en stock: {producto[0]['qty_available']}"
                        if quants:
                            resultados += "\n⌚Tiempo de entrega: "
                            for quant in quants:
                                if quant['location_id'][0] == 252:
                                    stockCEA += quant['quantity'] 
                                elif quant['location_id'][0] in provedoresIDs:
                                    stockProvedor += quant['quantity'] 
                        print(f"DEBUG[Provedor: {stockProvedor} CEA: {stockCEA}]")
                        if stockCEA > 0 and stockProvedor <= 0:
                            resultados += "Inmediato."
                        elif (stockCEA > 0 and stockProvedor > 0) and (stockProvedor > stockCEA or stockCEA > stockProvedor):
                            resultados += f"Entrega inmediata para pedidos de hasta {stockCEA} piezas. Para cantidades superiores a {stockCEA} piezas, el tiempo de entrega es de 3 a 5 días."
                        elif stockCEA <= 0 and stockProvedor > 0:
                            resultados += "De 3 a 5 dias."
                        
                    else:
                        arrNoExistencias.append(producto[0]['name'])
                        print("DEBUG[Producto sin existencias]")
                    resultados += "\n"
                    
                        
                else:
                    #Si no se encuentra se guarda el termino y se suma un contador 
                    countNotFounded += 1
                    arrnoEncontrados.append(cadena)
                    
            else:
                countFound = -1
        if arrnoEncontrados:#Se crea una lista en texto con los productos no encontrados
            for i, prod in enumerate(arrnoEncontrados):
                        if i == len(arrnoEncontrados) -1:
                            noEncontrados += prod.strip() + "."
                        else:
                            noEncontrados += prod.strip() + ", "
        if countFound >0:#Si hay resultados se crea un texto final y este varia..
            #Dependiendo si solo se encontro un producto o mas, se utilizan plurales
            if  countFound == 1:
                promt += "📦Este es el producto que podrias estar buscando:\n" + resultados
                if arrNoExistencias:
                    promt += "\n⚠️ Disponibilidad:\n"
                    promt += "Actualmente, el producto no se encuentra en stock, sin embargo, podemos solicitarlo directamente con el fabricante.\n"
                promt += f"""\npor favor, si estas interesado en este producto, """
            else:
                promt += "📦Estos son los productos que podrias estar buscando:\n" + resultados
                if len(arrNoExistencias) == 1:
                    promt += "\n⚠️ Disponibilidad:\n"
                    promt += f"\nActualmente, el producto {arrNoExistencias[0]} no se encuentra en stock, sin emgargo, podemos solicitarlo directamente con el fabricante.\n"
                if len(arrNoExistencias) > 1 and len(arrNoExistencias) != countFound:
                    stringProductos = ""
                    print(arrNoExistencias)
                    for i, producto in enumerate(arrNoExistencias):
                        if i == 0:
                            stringProductos += f"{arrNoExistencias[i]}"
                        elif i == len(arrNoExistencias) -1 :
                            stringProductos += f" y {arrNoExistencias[i]}"
                        else:
                            stringProductos += f", {arrNoExistencias[i]}"
                
                    promt += "\n⚠️ Disponibilidad:\n"
                    promt += f"\nActualmente, los productos {stringProductos} no se encuentran en stock, sin emgargo, podemos solicitarlos directamente con el fabricante.\n"
                elif len(arrNoExistencias) == countFound:    
                    promt += "\n⚠️ Disponibilidad:\n"
                    promt += f"\nActualmente, ninguno de los productos que solicitaste se encuentra en stock, sin emgargo, podemos solicitarlos directamente con el fabricante.\n"
                promt += f"""\npor favor, si estas interesado en alguno de estos productos, """
            promt += f"""proporcioname los siguientes datos:

👤 Nombre Completo
📞 Número de Teléfono
📧 Correo Electrónico
📍 Ciudad de Residencia
🧩 Número de Parte del/los producto(s) (y sus cantidades)"""
        elif countFound == -1:
            promt= f"""La cadena {cadena} no cumple con los criterios establecidos para ser reconocida como un número de parte válido."""
        else:#Del mismo modo, se crea un texto fiunal para los productos no encontrados
            promt += f"""No se encontraron en la base de datos productos que coinsidan con tu busqueda, por favor, 
se mas especifico o proporcioname el SKU del producto."""
        if noEncontrados:
            if countNotFounded == 1:
                promt += f"\n\nEl siguiente termino no fue encontrado en la base de datos: {noEncontrados}"
            else:
                promt += f"\n\nLos siguientes terminos no fueron encontrados en la base de datos: {noEncontrados}"
        return {
            'content':promt,
            'action': action,
            'products':arrEncontrados
        }


    #Este metodo toma los datos del cliente, redacta un correo para un agente de ventas y lo envia 
    def registrarCliente(self, entrada):
        #Declaracion de variables 
        msj = ""
        destination = self.destinationMail
        subject = "NUEVO LEAD DE VENTA CAPTURADO"
        cadena = re.findall(r"(?:REGISTRO_CLIENTE):\s*(.*)", entrada, re.DOTALL) #Se elimina el bloque contienen los datos
        
        #Configuracion de correos de destino 
        #Se captura la ciudad de residencia del cliente con una Regex
        city = re.search(r"Ciudad de residencia:\s*(.+)", entrada, re.IGNORECASE) 
        clientName = re.search(r"Nombre:\s*(.+)", entrada, re.IGNORECASE)
        clientEMail = re.search(r"Correo Electronico:\s(.+)", entrada, re.IGNORECASE)
        clientNumber = re.search(r"Numero de telefono:\s(.+)",entrada, re.IGNORECASE)
        products =  re.search(r"\[([^\]]*)\]",entrada, re.DOTALL)
        partnerID = 5353
        user_id = 22
        teamID = 1
        partnerName = 'Manuel'
        print(products)
        
        if city:
            print(f"DEBUG[Ciudad de residencia: {city.group(1)}]")
            #Si esta cadena extraida coincide con MTY o Monterrey, se asigna su mail correspondiente
            if re.search(r"\b(monterrey|mty)\b", city.group(1), re.IGNORECASE):
                destination = self.destinationMailMTY
                partnerID = 73
                partnerName = "Alis"
                user_id = 7
                teamID = 4
            elif re.search(r"\b(saltillo)\b", city.group(1), re.IGNORECASE):
                destination = self.destinationMailSaltillo
                partnerID = 5352
                user_id = 9
                teamID = 5
                partnerName = "Juan Jose"
        
    #Contiene el contenido del correo y se le añade la informacion
        content = f"""Hola {partnerName},
Se ha registrado una nueva oportunidad de venta en el portal oficial de CEA, a continuacion te 
comparto los datos para que puedas darle seguimiento. 

{cadena[0]}

Saludos,
CEA bot 
Asistente de ventas 
CEA: control y elementos de Automatizacion
"""    
        
        msj = self.confirmMsj
        
        
        self.createNewLead(city=city.group(1), name=clientName.group(1), email=clientEMail.group(1), phoneNumber=clientNumber.group(1), productList = products, userID = user_id, teamID=teamID, msjContent = content)             

        return {
            'content':msj,
            'action': 'none'
        }
    
    def procesUserData(self, entrada):
        
        user_id = 22
        teamID = 1
        partnerName = 'Manuel'
        nombre = re.search(r"Nombre:\s*(.+)", entrada)
        telefono = re.search(r"Teléfono:\s*(\d+)", entrada)
        correo = re.search(r"Correo:\s*([\w\.-]+@[\w\.-]+\.\w+)", entrada)
        ciudad = re.search(r"Ciudad:\s*(.+)", entrada)
        productos = re.findall(r"SKU\s+([\w\d]+):\s*(\d+)", entrada)

        cadena_productos = ""

        for sku, cantidad in productos:
            cadena_productos += f"{sku}:{cantidad}|"

        print(cadena_productos)
        
        if re.search(r"\b(monterrey|mty)\b", ciudad.group(1), re.IGNORECASE):
                partnerName = "Alis"
                user_id = 7
                teamID = 4
        elif re.search(r"\b(saltillo|sty)\b", ciudad.group(1), re.IGNORECASE):
                user_id = 9
                teamID = 5
                partnerName = "Juan Jose"
        content = f"""Hola {partnerName},
Se ha registrado una nueva oportunidad de venta en el portal oficial de CEA, a continuacion te 
comparto los datos para que puedas darle seguimiento. 

{entrada}

Saludos,
CEA bot 
Asistente de ventas 
CEA: control y elementos de Automatizacion
"""     
        self.createNewLead(city=ciudad.group(1), name=nombre.group(1), email=correo.group(1), phoneNumber=telefono.group(1), productList = cadena_productos, userID = user_id, teamID=teamID, msjContent = content)             
        
    
        
        return {
            'content':self.confirmMsj,
            'action':'none'
        }
        
    
        
            
    #Metodo que toma los datos del cliente proporcionados por el chatbot y agenda un lead de venta en Odoo
    def createNewLead(self, name, email, phoneNumber, productList, city, userID, teamID, msjContent):
        print(productList)
        tagsID = []
        arrDicProd = []
        arrprod = productList.split('|')
        totalPrice = 0
        print(arrprod)
        for prod in arrprod:
            print(prod)
            if prod == '':
                continue
            unidProduct = prod.split(':')
            arrDicProd.append({"sku":unidProduct[0], "unidades":unidProduct[1].replace(" ", "")})
        for dicProd in arrDicProd:
            product = self.models.execute_kw(
                self.odooDB,
                self.uid,
                self.odooPass,
                'product.template',
                'search_read',
                [[('name', '=', dicProd["sku"])]],
                {'fields':['name', 'list_price', 'x_studio_moneda' , 'x_studio_marca_1']}
                
            )
            if product[0]['x_studio_moneda']:
                if product[0]['x_studio_moneda'] == 'USD':
                    c = CurrencyConverter()
                    basePrice = c.convert(product[0]['list_price'],'USD', 'MXN')
                elif product[0]['x_studio_moneda'] == 'MXN':
                    basePrice = product[0]['list_price']
            else: 
                basePrice == 00
            totalPrice =+ basePrice * int(dicProd['unidades'])
            
            if product[0]['x_studio_marca_1'] == 'PATLITE':
                    tagsID.append(1)
            elif product[0]['x_studio_marca_1'] == 'PILZ':
                    tagsID.append(6)
            elif product[0]['x_studio_marca_1'] == 'Parker Hannifin':
                    tagsID.append(8)
            elif product[0]['x_studio_marca_1'] == 'CONTRINEX':
                    tagsID.append(14)
            elif product[0]['x_studio_marca_1'] == 'PHOENIX CONTACT':
                    tagsID.append(15)
        leadID = self.models.execute_kw(
                self.odooDB,
                self.uid,
                self.odooPass,
                'crm.lead',
                'create',
                [{
                    'name':f"CEAbot: Oportunidad capturada para {name} {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}",
                    'contact_name': name,
                    'email_from':email,
                    'phone': phoneNumber,
                    'expected_revenue': totalPrice,
                    'type':'opportunity',
                    'description': f"Posible cliente {name}, proviniente de {city} intersad@ en los productos {productList}",
                    'tag_ids': [(6,0, tagsID)],
                    'user_id': userID,
                    'team_id': teamID,
                    'company_id': 1
                }]
                )
        if leadID != 0:
            self.models.execute_kw(
                self.odooDB,
                self.uid,
                self.odooPass,
                'crm.lead',
                'message_post',
                [[leadID]],
                {
                    'body':msjContent,
                    'message_type':'comment',
                    'subtype_xmlid': 'mail.mt_comment'
                }
                
                
            )
            
            



    #Metodo post para la API que resive el mensaje del usuario devuelve la respuesta del modelos
    def post(self, request):
        messages = []
        #se rescive el historial de mensajes, ya que esta se debe almacenar desde
        #la aplicacion front
        history = request.data.get("messages",[])
        #Se resive el mensaje del usuario
        user_message = request.data.get("message")
        #Si el mensaje no es resivido el API responde con un mensaje de error
        if not user_message:
            return Response({"error":"No se recivio un mensaje de parte del usuario"}, status = 400)
        elif "Solicitud de Cotización" in user_message:
            print("Es una solicitud de cotización")
            return Response(self.procesUserData(user_message))
        elif user_message == "API_TEST":
            print("DEBUG[LA API ESTA ACTIVA]")
        else:
        #Se añade el historial de mensajes de la app front al de la API
            messages = self.messages.copy()
            if messages: 
               messages.append(history[-1])
            try:
                #Se llama al metodo chat y se pasa como parametro el historial de mensajes Global
                response = self.chat(messages)
                responseContent = response['content']
                response_text = ""
                #Si la REGEX coinside con el bloque de texto de consulta de datos se hace la llamada 
                #al metofo buscarProducto, la respuesta se pasa como respuesta del chatbot
                if re.search("(BUSCAR_PRODUCTO|Producto|producto):.*", responseContent ):
                    response_text = self.buscarByOdoo(responseContent)
                    #De la misma forma, si la REGUEX captura el bloque con los datos del cliente,
                    #se llama al metodo registrarCliente el resultado se devuelve como respuesta
                elif re.search("(REGISTRO_CLIENTE):.*",responseContent):
                    response_text = self.registrarCliente(responseContent)
                else:
                    response_text = response #en caso de que no sea ninguna de las dos, se pasa la respuesta del modelo
            
                    print(response_text['action'])
            
                return Response(response_text, status=200)
            
            
            except Exception as e:
                print("ERROR en respuesta de API:")
                traceback.print_exc() #
                return Response({"error": str(e)}, status=500)

