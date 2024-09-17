# Visual Studio Code + Anki

En Anki debemos tener el siguiente Add-ons:

[AnkiConnect](https://ankiweb.net/shared/info/2055492159)

Código: 2055492159

Este es opcional:

[Review Heatmap](https://ankiweb.net/shared/info/1771074083)

Código: 1771074083

Desde VSC creamos un archivo `.md` totalmente nuevo que contenga la tarjeta de la siguiente manera:

```md
	## Code to test

	```js
	const note = () => {
	  console.log("Message");
	};
	```
```

Añadir la siguiente extensión a Visual Studio Code:

[Anki for VSCode](https://marketplace.visualstudio.com/items?itemName=jasew.anki)

Seleccionamos `Extension settings`

![](https://i.postimg.cc/T1WkDqcG/29-anki-for-vsc.png)

Ahora buscamos: `Anki: Default Deck`, añadimos el nombre del `Deck` destino y cerramos.

Con esto listo presionamos `F1` y buscamos `Anki: Send To Deck`

😔👈 Si esto no funciona, haz lo siguiente para añadir código que se vea resaltado según la sintaxis.

## Add-ons: Code Highlight

Después de probar varios Add-ons me funcionó este:

[Code Highlight](https://ankiweb.net/shared/info/1415523481)

Código: 1415523481

Solo se debe envolver el código en la etiqueta `pre` y `code`, además, para obtener el resaltado según el lenguaje debes añadir la clase descrita abajo.

```js
<pre><code> ... </code></pre>

 <code class="language-js">
```

Si probaste este método verás que no se ve tan bien.

## Usando una librería

Para obtener un buen resaltado usaré [Prism](https://prismjs.com/)

Front Template:

```js
{{Front}}
```

Back Template:

```js
{{FrontSide}}

<hr id="answer" />

<pre>
  <code class="language-js">
{{Back}}
  </code>
</pre>

<link
  href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.27.0/themes/prism.min.css"
  rel="stylesheet"
/>
<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.27.0/prism.min.js"></script>
```

[Alternativa: Highlightjs](https://highlightjs.org/)

![](https://i.postimg.cc/d1S8dwGr/30-syntax-highlighting.png)