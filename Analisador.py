from typing import Tuple, Optional
import sys
import os

# ---------- Configurações ----------
MAX_IDENT_LEN = 64

# ---------- Palavras reservadas (tabela inicializada no começo) ----------
PALAVRAS_RESERVADAS = {
    'absolute', 'array', 'begin', 'case', 'char', 'const', 'div', 'do', 'dowto', 'else', 'end', 'external',
    'file', 'for', 'forward', 'func', 'function', 'goto', 'if', 'implementation', 'integer', 'interface', 'interrupt',
    'label', 'main', 'nil', 'nit', 'of', 'packed', 'proc', 'program', 'real', 'record', 'repeat', 'set', 'shl', 'shr',
    'string', 'then', 'to', 'type', 'unit', 'until', 'uses', 'var', 'while', 'with', 'xor'
}

# ---------- Tokens legíveis ----------
TOK_PALAVRA_RESERVADA = 'PALAVRA_RESERVADA'
TOK_IDENTIFICADOR = 'IDENTIFICADOR'
TOK_NUM_INT = 'NUM_INTEIRO'
TOK_NUM_REAL = 'NUM_REAL'
TOK_CONST_CHAR = 'CONST_CHAR'
TOK_CONST_STRING = 'CONST_STRING'
TOK_OP_ARIT = 'OP_ARITMETICO'
TOK_OP_REL = 'OP_RELACIONAL'
TOK_OP_LOG = 'OP_LOGICO'
TOK_SIMB_ESPEC = 'SIMBOLO_ESPECIAL'
TOK_ATRIB = 'ATRIBUICAO'
TOK_FIM = 'FIM'
TOK_ERRO = 'ERRO_LEXICO'

# símbolos simples que serão retornados como SIMBOLO_ESPECIAL
SIMBOLOS_ESPECIAIS = {',', ':', ';', '.', '(', ')'}

# operadores aritméticos
ARITMETICOS = {'+', '-', '*', '/'}
# operadores relacionais possíveis
RELACIONAIS = {'=', '>=', '<=', '>', '<', '<>'}
# operadores lógicos
LOGICOS = {'and', 'or', 'not'}
# palavra 'mod' como operador aritmético
PALAVRA_MOD = 'mod'

# ---------- Estrutura de Tabela de Símbolos ----------


class TabelaSimbolos:
    def __init__(self):
        self.tabela = {}

    def inserir(self, nome_original: str):
        key = nome_original.lower()
        if key in self.tabela:
            self.tabela[key]['ocorrencias'] += 1
        else:
            self.tabela[key] = {
                'nome_original': nome_original, 'ocorrencias': 1}
        return key

    def buscar(self, nome: str):
        return self.tabela.get(nome.lower())

    def __repr__(self):
        return str(self.tabela)

# ---------- Analisador Léxico ----------


class AnalisadorLexico:
    def __init__(self, texto: str):
        self.texto = texto
        self.pos = 0
        self.linha = 1
        self.coluna = 1
        self.tabela_simbolos = TabelaSimbolos()
        self.saida = []  # lista de (lexema, token, linha, coluna)

    # peek e advance para navegação
    def _peek(self) -> Optional[str]:
        return self.texto[self.pos] if self.pos < len(self.texto) else None

    def _advance(self) -> Optional[str]:
        ch = self._peek()
        if ch is None:
            return None
        self.pos += 1
        if ch == '\n':
            self.linha += 1
            self.coluna = 1
        else:
            self.coluna += 1
        return ch

    def _match(self, expected: str) -> bool:
        if self._peek() == expected:
            self._advance()
            return True
        return False

    def _is_letter(self, ch: str) -> bool:
        return ch.isalpha()

    def _is_digit(self, ch: str) -> bool:
        return ch.isdigit()

    # ignora espaços, tabs, enters e comentários
    def _skip_whitespace_and_comments(self):
        while True:
            ch = self._peek()
            if ch is None:
                return
            if ch.isspace():
                self._advance()
                continue
            # comentários de bloco /* ... */
            if ch == '/' and self.pos + 1 < len(self.texto) and self.texto[self.pos+1] == '*':
                self._advance()
                self._advance()  # consome /*
                while True:
                    c = self._peek()
                    if c is None:
                        self.saida.append(
                            ('/*Comentario_sem_fechamento', TOK_ERRO, self.linha, self.coluna))
                        return
                    if c == '*' and self.pos + 1 < len(self.texto) and self.texto[self.pos+1] == '/':
                        self._advance()
                        self._advance()
                        break
                    self._advance()
                continue
            break

    # função principal de tokenização
    def next_token(self) -> Tuple[Optional[str], Optional[str], int, int]:
        self._skip_whitespace_and_comments()
        ch = self._peek()
        if ch is None:
            return (None, None, self.linha, self.coluna)

        inicio_linha, inicio_coluna = self.linha, self.coluna

        # Identificador ou palavra reservada ou operadores-lógicos ou mod
        if self._is_letter(ch) or ch == '_':
            lex = ''
            while True:
                c = self._peek()
                if c is None or not (c.isalnum() or c == '_'):
                    break
                lex += self._advance()
            lex_lower = lex.lower()
            if len(lex) > MAX_IDENT_LEN:
                lex_trunc = lex[:MAX_IDENT_LEN]
                self.saida.append(
                    (lex_trunc, TOK_ERRO, inicio_linha, inicio_coluna))
                self.tabela_simbolos.inserir(lex_trunc)
                return (lex_trunc, TOK_IDENTIFICADOR, inicio_linha, inicio_coluna)
            if lex_lower in PALAVRAS_RESERVADAS:
                return (lex, TOK_PALAVRA_RESERVADA, inicio_linha, inicio_coluna)
            if lex_lower in LOGICOS:
                return (lex, TOK_OP_LOG, inicio_linha, inicio_coluna)
            if lex_lower == PALAVRA_MOD:
                return (lex, TOK_OP_ARIT, inicio_linha, inicio_coluna)
            self.tabela_simbolos.inserir(lex)
            return (lex, TOK_IDENTIFICADOR, inicio_linha, inicio_coluna)

        # Números: inteiro ou real
        if self._is_digit(ch):
            lex = ''
            while self._peek() and self._is_digit(self._peek()):
                lex += self._advance()
            # decimal
            if self._peek() == '.' and self.pos + 1 < len(self.texto) and self.texto[self.pos+1].isdigit():
                lex += self._advance()
                while self._peek() and self._is_digit(self._peek()):
                    lex += self._advance()
                # expoente
                if self._peek() and self._peek().lower() == 'e':
                    lex += self._advance()
                    if self._peek() in ('+', '-'):
                        lex += self._advance()
                    if not self._peek() or not self._is_digit(self._peek()):
                        self.saida.append(
                            (lex, TOK_ERRO, inicio_linha, inicio_coluna))
                        return (lex, TOK_ERRO, inicio_linha, inicio_coluna)
                    while self._peek() and self._is_digit(self._peek()):
                        lex += self._advance()
                return (lex, TOK_NUM_REAL, inicio_linha, inicio_coluna)
            # expoente sem ponto
            if self._peek() and self._peek().lower() == 'e':
                lex += self._advance()
                if self._peek() in ('+', '-'):
                    lex += self._advance()
                if not self._peek() or not self._is_digit(self._peek()):
                    self.saida.append(
                        (lex, TOK_ERRO, inicio_linha, inicio_coluna))
                    return (lex, TOK_ERRO, inicio_linha, inicio_coluna)
                while self._peek() and self._is_digit(self._peek()):
                    lex += self._advance()
                return (lex, TOK_NUM_REAL, inicio_linha, inicio_coluna)
            return (lex, TOK_NUM_INT, inicio_linha, inicio_coluna)

        # Constantes char e string
        if ch == '\'':
            lex = self._advance()
            content = ''
            c = self._peek()
            if c is None:
                return ("'", TOK_ERRO, inicio_linha, inicio_coluna)
            if c == '\\':
                content += self._advance()
                if self._peek():
                    content += self._advance()
            else:
                content += self._advance()
            if self._peek() == '\'':
                lex += content + self._advance()
                return (lex, TOK_CONST_CHAR, inicio_linha, inicio_coluna)
            else:
                while self._peek() and self._peek() != '\'':
                    self._advance()
                if self._peek() == "'":
                    self._advance()
                return (lex + content, TOK_ERRO, inicio_linha, inicio_coluna)
        if ch == '"':
            lex = self._advance()
            content = ''
            while True:
                c = self._peek()
                if c is None:
                    return (lex + content, TOK_ERRO, inicio_linha, inicio_coluna)
                if c == '"':
                    lex += content + self._advance()
                    return (lex, TOK_CONST_STRING, inicio_linha, inicio_coluna)
                content += self._advance()

        # Operadores e símbolos
        if ch == ':':
            self._advance()
            if self._match('='):
                return (':=', TOK_ATRIB, inicio_linha, inicio_coluna)
            return (':', TOK_SIMB_ESPEC, inicio_linha, inicio_coluna)
        if ch in ('>', '<', '='):
            c = self._advance()
            nextc = self._peek()
            if c == '>' and nextc == '=':
                self._advance()
                return ('>=', TOK_OP_REL, inicio_linha, inicio_coluna)
            if c == '<' and nextc == '=':
                self._advance()
                return ('<=', TOK_OP_REL, inicio_linha, inicio_coluna)
            if c == '<' and nextc == '>':
                self._advance()
                return ('<>', TOK_OP_REL, inicio_linha, inicio_coluna)
            return (c, TOK_OP_REL, inicio_linha, inicio_coluna)
        if ch == '.':
            self._advance()
            return ('.', TOK_FIM, inicio_linha, inicio_coluna)
        if ch in SIMBOLOS_ESPECIAIS:
            self._advance()
            return (ch, TOK_SIMB_ESPEC, inicio_linha, inicio_coluna)
        if ch in ARITMETICOS:
            lex = self._advance()
            return (lex, TOK_OP_ARIT, inicio_linha, inicio_coluna)

        unknown = self._advance()
        return (unknown, TOK_ERRO, inicio_linha, inicio_coluna)

    # loop de análise completo
    def analisar(self):
        while True:
            lex, tok, linha, coluna = self.next_token()
            if lex is None and tok is None:
                break
            self.saida.append((lex, tok, linha, coluna))
        return self.saida

# ---------- Utilitários de I/O ----------


def ler_arquivo_caminho(caminho: str) -> str:
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(
            f"Arquivo '{caminho}' não encontrado. Crie o arquivo com o código fonte.")
        sys.exit(1)


def escrever_saida(caminho: str, pares):
    with open(caminho, 'w', encoding='utf-8') as f:
        for lex, tok, linha, coluna in pares:
            f.write(f"<{lex}, {tok}, linha {linha}, coluna {coluna}>\n")


# ---------- Executável principal ----------
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python Analisador.py <arquivo_teste.txt>")
        sys.exit(1)

    input_file = sys.argv[1]
    texto = ler_arquivo_caminho(input_file)

    lexer = AnalisadorLexico(texto)
    pares = lexer.analisar()

    # gera arquivo de saída com nome do arquivo de entrada
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_saida.txt"
    escrever_saida(output_file, pares)

    print(
        f"Análise concluída. {len(pares)} tokens gravados em '{output_file}'.")
    print("Tabela de símbolos (identificadores):")
    for k, v in lexer.tabela_simbolos.tabela.items():
        print(f"  {v['nome_original']} -> ocorrencias: {v['ocorrencias']}")
