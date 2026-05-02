from flask import Flask, render_template

app = Flask(__name__)

# Lista completa e revisada com caminhos de pastas específicos
produtos = [
    # CARNES (static/carnes)
    {"id": 1, "nome": "Picanha Fatiada", "preco": 59.90, "categoria": "Carnes", "imagem": "carnes/picanha.jpg"},
    {"id": 2, "nome": "Carne Suína", "preco": 24.90, "categoria": "Carnes", "imagem": "carnes/suina.jpg"},
    {"id": 3, "nome": "Peito de Frango", "preco": 18.90, "categoria": "Carnes", "imagem": "carnes/frngo.jpg"},
    
    # BEBIDAS (static/bebidas)
    {"id": 13, "nome": "Refrigerantes Variados", "preco": 8.90, "categoria": "Bebidas", "imagem": "bebidas/refrigerantes.jpg"},
    {"id": 14, "nome": "Sucos Del Valle", "preco": 4.50, "categoria": "Bebidas", "imagem": "bebidas/sucos.jpg"},
    {"id": 15, "nome": "Vinhos Tradição", "preco": 25.00, "categoria": "Bebidas", "imagem": "bebidas/vinhos.jpg"},

    # FRIOS (static/frios)
    {"id": 16, "nome": "Mortadela Perdigão", "preco": 12.90, "categoria": "Frios", "imagem": "frios/mortadella.jpg"},
    {"id": 17, "nome": "Muçarela em Barra", "preco": 32.00, "categoria": "Frios", "imagem": "frios/muçarela.jpg"},
    {"id": 18, "nome": "Presunto Cozido", "preco": 15.50, "categoria": "Frios", "imagem": "frios/presunto.jpg"},
    
    # HORTIFRUTI (static/hortifruti)
    {"id": 4, "nome": "Alface Lisa", "preco": 3.50, "categoria": "Hortifruti", "imagem": "hortifruti/alface.jpg"},
    {"id": 5, "nome": "Batata Inglesa", "preco": 4.50, "categoria": "Hortifruti", "imagem": "hortifruti/batata.jpg"},
    {"id": 6, "nome": "Cebola", "preco": 3.80, "categoria": "Hortifruti", "imagem": "hortifruti/cebola.jpg"},
    
    # MERCEARIA (static/mercearia)
    {"id": 10, "nome": "Arroz Prato Fino", "preco": 28.90, "categoria": "Mercearia", "imagem": "mercearia/arroz.jpg"},
    {"id": 11, "nome": "Feijão Kicaldo", "preco": 7.50, "categoria": "Mercearia", "imagem": "mercearia/feijao.jpg"},
    {"id": 12, "nome": "Açúcar Cristal", "preco": 16.90, "categoria": "Mercearia", "imagem": "mercearia/acucar.jpg"},

    # LIMPEZA (static/limpeza)
    {"id": 7, "nome": "Detergente Veja", "preco": 2.20, "categoria": "Limpeza", "imagem": "limpeza/detergente.jpg"},
    {"id": 8, "nome": "Vassoura de Nylon", "preco": 15.90, "categoria": "Limpeza", "imagem": "limpeza/vassoura.jpeg"},
    {"id": 9, "nome": "Pazinha de Lixo", "preco": 5.50, "categoria": "Limpeza", "imagem": "limpeza/pazinha.jpg"},
]

@app.route('/')
def index():
    return render_template('index.html', produtos=produtos)

if __name__ == '__main__':
    app.run(debug=True)