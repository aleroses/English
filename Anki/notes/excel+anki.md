# Excel + Anki

## Actualizar Deck existente

Actualmente, tengo un Deck con 9 campos a los que añadiré 2 campos nuevos para colocar traducciones.

Para empezar revisemos los tipos de notas existentes, esto será de utilidad más tarde.

Herramientas / Administrar tipo de notas:

![](https://i.postimg.cc/d0LWHYdm/15-note-types.png)

Por defecto tengo estos tipos:

![](https://i.postimg.cc/kMTmDx92/16-note-types-default.png)

Lo que haré para hacer algunas pruebas sin perjudicar a mi deck original, es subir (doble click) este deck a otra cuenta.

![](https://i.postimg.cc/pTcbpH8m/17-deck.png)

Ahora si revisamos nuevamente los tipos de notas, veremos que se añadieron nuevos.

![](https://i.postimg.cc/xTwRn4kn/18-new-note-types.png)

Los nuevos tipos son:

- `4000 EEW [3600 notes]`
- `4000 EEW Extra [271 notes]`

Si revisamos los campos vemos:

![](https://i.postimg.cc/g2DH8qcZ/19-note-type-fields.png)

Para este caso los campos que me interesan son `9: Meaning_transaltion` y `11: Example_translation` que contendrán las traducciones de los campos `8: Meaning` y `10: Example`.

Si en tu caso aún no agregaste los nuevos campos, puedes hacer desde aquí. Esto te puede evitar algunos errores a futuro.

Hay otra forma de añadir campos pero creo que puede traer problemas, te la muestro a continuación:

Entramos a `Browse`

![](https://i.postimg.cc/vH32rsZh/20-browse.png)

Del lado izquierdo seleccionamos el deck específico con el que vamos a trabajar.

![](https://i.postimg.cc/C1g9v4Ts/21-browse-deck.png)

Desde la sección de campos o Field añadimos los que vayamos a necesitar.

![](https://i.postimg.cc/SRQpy8BS/1-fields.png)

Por el momento estos estarán vacíos.

![](https://i.postimg.cc/PqBWsQ8D/2-empty-fields.png)

Para que el contenido que agreguemos a estos nuevos campos se logre visualizar en nuestras tarjetas debemos añadir los campos dentro del HTML de la tarjeta. Para esto usamos `{nombre del campo}`.

![](https://i.postimg.cc/DzFhCtx4/3-cards.png)

![](https://i.postimg.cc/VNBCpP1x/4-cards-fields.png)

Por el momento las tarjetas se ven así:

![](https://i.postimg.cc/SRxBb7QF/22-front-card.png)

![](https://i.postimg.cc/rphbCRCf/23-back-card.png)


### Exportar Deck

Para este caso en particular necesitamos exportar el deck en formato Texto plano `.txt`.

![](https://i.postimg.cc/XJBp3M0N/5-export.png)

![](https://i.postimg.cc/d3TH80cM/6-export-plain-text.png)

Una vez exportado copiamos el contenido del archivo `.txt` dentro de un archivo Excel, esto lo podemos lograr de la siguiente manera:

- Abrir archivo en un block de notas:
	- Clic derecho / Abrir con / Notepad
- Usa `Ctrl + A` para seleccionar todo
- `Ctrl + C` para copiar
- Usa `Ctrl + V` para pegar en la primera celda de Excel
- Si notas que se pegó de manera extraña usa `Ctrl + Shift + V` 👈👀 en lugar de solo `Ctrl + V`. 


![](https://i.postimg.cc/t4rcQw5M/7-copy-text.png)

![](https://i.postimg.cc/0QvDt2SR/8-paste-text.png)

### Editar archivo Excel

Añade cabeceras iguales a como estaba en Anki y de no existir crea las columnas donde irá la nueva información.

![](https://i.postimg.cc/9M4Kph6h/9-header.png)

### Traducir con ChatGPT

Usemos ChatGPT para crear traducciones, pero antes:

- Crea una nueva hoja en Excel.
- Copia y pega las columnas a traducir.

```md
|Meaning |Meaning Translate |Example |Example Translate |
|Text... |                  |Text... |                  |
|Text... |                  |Text... |                  |
|Text... |                  |Text... |                  |
|Text... |                  |Text... |                  |
|Text... |                  |Text... |                  |
```

📌 Esto servirá para revisar las traducciones entregadas por ChatGPT, ya que a veces se equivoca y toca corregir.

Ahora sí:

Copia las primeras 20 filas (recomendado) y usa el **Prompt** de abajo para que GPT logre traducir con éxito lo que necesitas. 

Si ChatGPT se detiene dale a continuar para que termine con las 20 oraciones.

```md
Tengo una tabla de las siguientes columnas:

Meaning
Meaning_translation
Example
Example_translation

Meaning tiene oraciones que me gustaría que estén traducidas al castellano en la columna Meaning_translation y de la misma manera con Example. 

Podrías entregarme una tabla numerada con las traducciones de Meaning en la columna Meaning_translation y de Example en la columna Example_translation.

Si alguna palabra tiene etiquetas HTML, no las quites, entrégame la información en la misma forma que te la he dado en las 4 columnas.
```

Antes:

![](https://i.postimg.cc/XvKrqFFD/24-prompt.png)

Entrega:

![](https://i.postimg.cc/ZqJTfQBV/25-result.png)

Ahora, copia el resultado y pégalo en la nueva hoja. Verifica que el contenido entregado sea correcto (Yo verifico de 10 en 10).

Una vez revisado el contenido ya puedes pegarlo en la tabla real.

![](https://i.postimg.cc/m2QYH566/10-result.png)

### Exportar a CSV UTF-8

Para que Anki reconozca el nuevo contenido debemos tenerlo en formato `.csv` para esto:

- Exporta en formato CSV UTF-8 (Delimitado por comas `*.csv`). 
	- File / Guardar como / Elige la carpeta / 
	- Guardar como tipo: **CSV UTF-8** (Delimitado por comas `*.csv`)
	- Guardar

- Abre el archivo CSV en Excel quita las cebeceras, y dale guardar. 

📌 Recuerda que todas las columnas deben corresponder a los campos que tenemos en Anki.

![](https://i.postimg.cc/DyqNw5Q7/11-file-csv.png)

### Importar archivo CSV

Entramos en Anki, seleccionamos el deck a actualizar.

![](https://i.postimg.cc/hjf6t8Q9/26-select-deck.png)

 Importamos el archivo CSV.

![](https://i.postimg.cc/PJZtPnvz/27-import-deck.png)

- Archivo / Importar / Elige el archivo CSV.
- File:
	- Seleccionamos Coma
	- Permitimos el uso de HTML en los campos.
- Import options:
	- Seleccionar el Deck padre y el deck hijo a actualizar.

![](https://i.postimg.cc/MHh8JT8t/12-separator-html.png)

![](https://i.postimg.cc/bw1SMSjC/13-import-options.png)

📌 Esto es importante: En el Mapeo de campo o Field mapping solo elegimos los campos a editar y lo demás lo dejamos en `(Nothing)` a excepción del primer campo que no permite cambiarlo.

![](https://i.postimg.cc/g0njpw9b/14-field-mapping.png)

Terminamos dando en **Importar**.



> Si hiciste como yo que no actualizaste todas las tarjetas del mazo y vez que algunas tarjetas no tienen los datos en los dos campos que agregamos, es por eso, solo actualizamos una parte, mañana seguiremos añadiendo más información a Excel y así hasta acabar con todas las tarjetas. Recuerda seguir los mismos pasos.