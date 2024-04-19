import argparse, time, openai, ast, os
from typing import Union
from bs4 import BeautifulSoup as bs
from ebooklib import epub
from rich import print
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()


class ChatGPT:
    def __init__(self, key):
        # Armazena a chave da API da OpenAI para ser usada nas requisições
        self.key = key

    def translate(self, text):
        # print(text)
        # Define a chave da API da OpenAI para autenticar as requisições
        openai.api_key = self.key
        try:
            # Envia a requisição de tradução para a API da OpenAI
            completion = openai.ChatCompletion.create(
                # Define o modelo a ser usado na requisição de tradução
                model="gpt-3.5-turbo",
                messages=[
                    {
                        # Define o papel do usuário na conversa com o modelo
                        "role": "user",
                        # Define o conteúdo da mensagem a ser enviada ao modelo, que é uma solicitação de tradução para português do Brasil mantendo o mesmo formato do texto original
                        "content": f"Please help me to translate `{text}` to Brazilian Portuguese, please return only translated content not include the origin text, maintain the same formatting as the original textual list individual elements ",
                    }
                ],
            )
            # Extrai o texto traduzido da resposta da API
            t_text = (
                completion["choices"][0]
                .get("message")
                .get("content")
                .encode("utf8")
                .decode()
            )
            # Remove as quebras de linha do texto traduzido
            t_text = t_text.strip("\n")
            try:
                # Tenta avaliar o texto traduzido como uma expressão Python literal
                t_text = ast.literal_eval(t_text)
            except Exception:
                # Caso a avaliação falhe, ignora o erro e mantém o texto traduzido como string
                pass
            # Aguarda 3 segundos antes de retornar o texto traduzido para evitar requisições muito frequentes à API
            time.sleep(3)
        except Exception as e:
            # Caso ocorra alguma exceção na requisição à API, imprime a mensagem de erro e aguarda 60 segundos antes de tentar novamente
            print(str(e), "will sleep 60 seconds")
            # Repete a requisição de tradução à API
            time.sleep(60)
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Please help me to translate `{text}` to Brazilian Portuguese, please return only translated content not include the origin text, maintain the same formatting as the original textual list individual elements",
                    }
                ],
            )
            t_text = (
                completion["choices"][0]
                .get("message")
                .get("content")
                .encode("utf8")
                .decode()
            )
            t_text = t_text.strip("\n")
            try:
                t_text = ast.literal_eval(t_text)
            except Exception:
                pass
        # print(t_text)
        # Retorna o texto traduzido
        return t_text


class BEPUB:
    """
    Classe responsável por traduzir um livro EPUB.

    Args:
        epub_name (str): O nome do arquivo EPUB a ser traduzido.
        key (str): A chave para inicializar a classe ChatGPT para realizar a tradução do texto.
        batch_size (int): O tamanho do lote de texto a ser traduzido de cada vez.

    Attributes:
        epub_name (str): O nome do arquivo EPUB a ser traduzido.
        translate_model (ChatGPT): A instância da classe ChatGPT para realizar a tradução do texto.
        origin_book (EpubBook): O livro EPUB original a ser traduzido.
        batch_size (int): O tamanho do lote de texto a ser traduzido de cada vez.

    Methods:
        translate_book: Traduz o livro EPUB.
        __translate_tag: Traduz as tags HTML específicas em um arquivo HTML do livro EPUB.

    """

    def __init__(self, epub_name, key, batch_size):
        self.epub_name = epub_name
        self.translate_model = ChatGPT(key)
        self.origin_book = epub.read_epub(self.epub_name)
        self.batch_size = batch_size

    def translate_book(self):
        """
        Traduz o livro EPUB.

        Cria um novo objeto do tipo EpubBook para armazenar o livro traduzido.
        Copia os metadados do livro original para o livro traduzido.
        Copia a coluna vertebral do livro original para o livro traduzido.
        Copia o sumário do livro original para o livro traduzido.
        Itera sobre todos os itens do livro original.
        Verifica se o item é um arquivo HTML.
        Parseia o conteúdo do arquivo HTML usando a biblioteca BeautifulSoup.
        Traduz as tags HTML específicas no arquivo HTML.
        Verifica se ainda há parágrafos na lista a serem traduzidos.
        Traduz o lote de parágrafos restante.
        Substitui cada parágrafo pelo texto traduzido correspondente.
        Atualiza o conteúdo do arquivo HTML com os parágrafos traduzidos.
        Adiciona o item atualizado ao livro traduzido.
        Extrai o nome base do arquivo EPUB original.
        Salva o livro traduzido em um novo arquivo EPUB.

        """
        new_book = epub.EpubBook()
        new_book.metadata = self.origin_book.metadata
        new_book.spine = self.origin_book.spine
        new_book.toc = self.origin_book.toc
        batch = {
            "content": [],
            "count": 0,
        }
        for i in self.origin_book.get_items():
            if i.get_type() == 9:
                soup = bs(i.content, "html.parser")
                name: str = i.get_name()

                # Traduz as tags HTML específicas no arquivo HTML
                self.__translate_tag("h1", name, soup, batch)  # Traduz as tags h1
                self.__translate_tag("h2", name, soup, batch)  # Traduz as tags h2
                self.__translate_tag("h3", name, soup, batch)  # Traduz as tags h3
                self.__translate_tag("h4", name, soup, batch)  # Traduz as tags h4
                self.__translate_tag("h5", name, soup, batch)  # Traduz as tags h5
                self.__translate_tag("h6", name, soup, batch)  # Traduz as tags h6
                self.__translate_tag("p", name, soup, batch)  # Traduz as tags p

                # Traduz o lote de parágrafos restante
                if batch["content"]:
                    translated_batch = self.translate_model.translate(
                        [p.text for p in batch["content"]]
                    )
                    for j, c_p in enumerate(batch["content"]):
                        c_p.string = c_p.text + translated_batch[j]
                    batch["content"] = []
                    batch["count"] = 0

                i.content = soup.prettify().encode()
            new_book.add_item(i)
        name = self.epub_name.split(".")[0]
        epub.write_epub(f"{name}_translated.epub", new_book, {})

    def __translate_tag(
        self, tag: str, item_name: str, soup: bs, batch: dict[str, Union[str, any]]
    ) -> None:
        """
        Traduz as tags HTML específicas em um arquivo HTML do livro EPUB.

        Args:
            tag (str): A tag HTML a ser traduzida.
            item_name (str): O nome do item do livro EPUB.
            soup (BeautifulSoup): O objeto BeautifulSoup que representa o arquivo HTML.

        """
        part_list = soup.findAll(tag)
        print(f"Traduzindo {len(part_list)} {tag} em {item_name}")
        for part in tqdm(part_list):
            if part.text and not part.text.isdigit():
                batch["content"].append(part)
                batch["count"] += 1
                if batch["count"] == self.batch_size:
                    translated_batch = self.translate_model.translate(
                        [part_.text for part_ in batch["content"]]
                    )
                    batch["content"][-1].string = batch["content"][-1].text + "".join(
                        map(str, translated_batch)
                    )
                    batch["content"] = []
                    batch["count"] = 0


if __name__ == "__main__":
    # Cria um parser de argumentos para a interface de linha de comando
    parser = argparse.ArgumentParser()
    # Adiciona um argumento para o nome do arquivo EPUB a ser traduzido
    parser.add_argument(
        "--book_name",
        dest="book_name",
        type=str,
        help="your epub book name",
    )
    # Adiciona um argumento para o tamanho do lote de texto a ser traduzido de cada vez
    parser.add_argument(
        "--batch_size",
        dest="batch_size",
        type=int,
        default=2,
        choices=[2, 3, 4, 5],
        help="the batch size paragraph for translation , max is 5",
    )
    # Parseia os argumentos da linha de comando
    options = parser.parse_args()

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or None
    if not OPENAI_API_KEY:
        # Verifica se a chave da API da OpenAI foi fornecida
        raise Exception("Need openai API key, please google how to")
    if not options.book_name.endswith(".epub"):
        # Verifica se o arquivo fornecido é do tipo EPUB
        raise Exception("please use epub file")
    # Inicializa a classe BEPUB com os parâmetros fornecidos
    e = BEPUB(options.book_name, OPENAI_API_KEY, options.batch_size)
    # Chama o método para traduzir o livro
    e.translate_book()
