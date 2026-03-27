import re
import random
import string
import base64
import math

class LuaObfuscator:
    def __init__(self):
        self.LUA_KEYWORDS = {
            "and","break","do","else","elseif","end","false","for",
            "function","goto","if","in","local","nil","not","or",
            "repeat","return","then","true","until","while"
        }
        self.ROBLOX_GLOBALS = {
            "game","workspace","script","Instance","Vector3","CFrame",
            "UDim2","Color3","BrickColor","Enum","math","string","table",
            "pairs","ipairs","next","type","tostring","tonumber","print",
            "warn","error","pcall","xpcall","select","unpack","rawget",
            "rawset","setmetatable","getmetatable","require","wait","task",
            "RunService","Players","TweenService","UserInputService",
            "ReplicatedStorage","Workspace","HttpService","spawn","delay",
            "coroutine","io","os","tick","time","typeof","assert","collectgarbage"
        }
        self._var_map = {}
        self._stats = {
            "vars_renamed": 0,
            "strings_encoded": 0,
            "junk_added": 0
        }

    def _random_name(self, length=None):
        """Gera nome de variável ofuscado que parece legítimo mas não é."""
        if length is None:
            length = random.randint(6, 14)
        # Nomes que parecem variáveis reais mas são aleatórios
        prefixes = ["_0x", "l1", "Il", "lI", "I1", "ll", "II"]
        prefix = random.choice(prefixes)
        chars = "lI1" * 3 + string.ascii_letters
        suffix = "".join(random.choices(chars, k=length))
        return prefix + suffix

    def _encode_string_hex(self, s):
        """Codifica string como escape hexadecimal Lua."""
        encoded = ""
        for ch in s:
            encoded += f"\\{ord(ch)}"
        return f'("{encoded}")'

    def _encode_string_table(self, s):
        """Codifica string como tabela de bytes com concat."""
        if len(s) == 0:
            return '("")'
        parts = [str(ord(c)) for c in s]
        chunks = [parts[i:i+8] for i in range(0, len(parts), 8)]
        table_str = "{" + ",".join(parts) + "}"
        return f'(function(t) local s="" for _,v in ipairs(t) do s=s..string.char(v) end return s end)({table_str})'

    def _encode_number(self, n):
        """Ofusca um número com operação matemática equivalente."""
        ops = [
            lambda x: f"({x + random.randint(1,99)}-{random.randint(1,99)})",
            lambda x: f"math.floor({float(x)}+0.0)",
            lambda x: f"(function() return {x} end)()",
            lambda x: f"({x*2}/2)" if x != 0 else f"(1-1)",
            lambda x: f"bit32.bxor({x ^ 0xFF},0xFF)" if 0 <= x <= 255 else str(x),
        ]
        try:
            n_int = int(n)
            if -1000 < n_int < 1000:
                return random.choice(ops)(n_int)
        except:
            pass
        return str(n)

    def _find_variables(self, code):
        """Encontra declarações de variáveis locais no código."""
        pattern = r'\blocal\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = re.findall(pattern, code)
        var_set = set()
        for m in matches:
            if m not in self.LUA_KEYWORDS and m not in self.ROBLOX_GLOBALS:
                var_set.add(m)
        return var_set

    def _find_functions(self, code):
        """Encontra funções locais nomeadas."""
        patterns = [
            r'\blocal\s+function\s+([a-zA-Z_][a-zA-Z0-9_]*)\b',
            r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
        ]
        funcs = set()
        for p in patterns:
            for m in re.findall(p, code):
                if m not in self.LUA_KEYWORDS and m not in self.ROBLOX_GLOBALS:
                    funcs.add(m)
        return funcs

    def _rename_vars(self, code):
        """Renomeia variáveis e funções locais."""
        targets = self._find_variables(code) | self._find_functions(code)
        self._var_map = {}
        for var in targets:
            self._var_map[var] = self._random_name()

        for original, renamed in self._var_map.items():
            # Substituição de palavra inteira, evitando globals
            code = re.sub(
                r'\b' + re.escape(original) + r'\b',
                renamed,
                code
            )
        self._stats["vars_renamed"] = len(self._var_map)
        return code

    def _encode_strings(self, code):
        """Codifica strings literais no código."""
        count = 0

        def replace_double(m):
            nonlocal count
            s = m.group(1)
            if len(s) == 0 or len(s) > 80:
                return m.group(0)
            count += 1
            method = random.choice(["hex", "table"])
            if method == "hex":
                return self._encode_string_hex(s)
            else:
                return self._encode_string_table(s)

        def replace_single(m):
            nonlocal count
            s = m.group(1)
            if len(s) == 0 or len(s) > 80:
                return m.group(0)
            count += 1
            return self._encode_string_hex(s)

        # Strings com aspas duplas (evita strings com escapes complexos)
        code = re.sub(r'"((?:[^"\\]|\\.)*)"', replace_double, code)
        # Strings com aspas simples
        code = re.sub(r"'((?:[^'\\]|\\.)*)'", replace_single, code)

        self._stats["strings_encoded"] = count
        return code

    def _encode_numbers(self, code):
        """Ofusca números inteiros simples."""
        def replace_num(m):
            full = m.group(0)
            # Não ofuscar números em rbxassetid ou contextos especiais
            return self._encode_number(full)

        # Apenas inteiros pequenos isolados (fora de strings já codificadas)
        code = re.sub(r'(?<!["\'\w\\.\\])\b([1-9]\d{0,3})\b(?!["\'\w])', 
                      lambda m: self._encode_number(m.group(0)), code)
        return code

    def _generate_junk_block(self):
        """Gera um bloco de código lixo que não faz nada."""
        junks = [
            lambda: f"local {self._random_name()} = nil",
            lambda: f"local {self._random_name()} = {random.randint(0,9999)}",
            lambda: (
                f"local {self._random_name(5)} = {{}}\n"
                f"for _={random.randint(1,3)},{random.randint(4,8)} do end"
            ),
            lambda: f"local {self._random_name()} = math.floor(0)",
            lambda: f"if false then local {self._random_name()} = true end",
            lambda: (
                f"do\n"
                f"  local {self._random_name()} = type(nil)\n"
                f"  local {self._random_name()} = {random.randint(0,100)}\n"
                f"end"
            ),
            lambda: f"local {self._random_name()} = string.format(\"%s\", \"\")",
            lambda: f"local {self._random_name()} = table.concat({{}})",
        ]
        return random.choice(junks)()

    def _add_junk_code(self, code, density=3):
        """Injeta código lixo em pontos aleatórios."""
        lines = code.split("\n")
        result = []
        junk_count = 0

        for i, line in enumerate(lines):
            result.append(line)
            # Insere junk após linhas locais/end com probabilidade baseada no density
            if random.randint(1, 10) <= density:
                stripped = line.strip()
                if stripped and not stripped.startswith("--"):
                    result.append(self._generate_junk_block())
                    junk_count += 1

        self._stats["junk_added"] = junk_count
        return "\n".join(result)

    def _remove_comments(self, code):
        """Remove comentários do código."""
        # Remove comentários de bloco --[[ ... ]]
        code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
        # Remove comentários de linha --
        code = re.sub(r'--[^\n]*', '', code)
        return code

    def _wrap_bytecode_style(self, code):
        """
        Nível 3: Envolve o código em um loader que decodifica base64.
        Simula estrutura de bytecode encoder.
        """
        encoded = base64.b64encode(code.encode()).decode()
        # Divide em chunks para parecer mais complexo
        chunk_size = 60
        chunks = [encoded[i:i+chunk_size] for i in range(0, len(encoded), chunk_size)]
        chunk_var = self._random_name()
        decode_var = self._random_name()
        run_var = self._random_name()
        concat_var = self._random_name()

        chunk_lines = [f'  "{c}",' for c in chunks]
        chunks_str = "\n".join(chunk_lines)

        wrapper = (
            f"local {chunk_var} = {{\n{chunks_str}\n}}\n"
            f"local {concat_var} = table.concat({chunk_var})\n"
            f"local {decode_var} = (function(b)\n"
            f"  local t = {{}}\n"
            f"  local i = 0\n"
            f"  local n = #b\n"
            f"  local r = ''\n"
            f"  for p = 1, n, 4 do\n"
            f"    local c = 0\n"
            f"    for j = 0, 3 do\n"
            f"      local ch = string.byte(b, p+j) or 61\n"
            f"      local v\n"
            f"      if ch >= 65 and ch <= 90 then v = ch-65\n"
            f"      elseif ch >= 97 and ch <= 122 then v = ch-71\n"
            f"      elseif ch >= 48 and ch <= 57 then v = ch+4\n"
            f"      elseif ch == 43 then v = 62\n"
            f"      elseif ch == 47 then v = 63\n"
            f"      else v = 0 end\n"
            f"      c = c * 64 + v\n"
            f"    end\n"
            f"    for j = 16, 0, -8 do\n"
            f"      if p+3 <= n or j ~= 0 then\n"
            f"        r = r .. string.char(math.floor(c / (2^j)) % 256)\n"
            f"      end\n"
            f"    end\n"
            f"  end\n"
            f"  return r\n"
            f"end)({concat_var})\n"
            f"local {run_var} = loadstring or load\n"
            f"if {run_var} then {run_var}({decode_var})() end\n"
        )
        return wrapper

    def _shuffle_locals(self, code):
        """Reorganiza declarações locais no início de blocos (nível 2+)."""
        # Agrupa locals no topo de funções — simulação simples
        return code  # Placeholder para não quebrar lógica

    def obfuscate(self, code: str, level: int = 2) -> str:
        """
        Ofusca o código Lua.
        level 1: leve  — remove comments, renomeia vars, hex strings
        level 2: médio — nível 1 + junk code + encode numbers
        level 3: max   — nível 2 + base64 wrapper (bytecode-style)
        """
        self._stats = {"vars_renamed": 0, "strings_encoded": 0, "junk_added": 0}

        # Nível 3: wrapping antes de tudo
        if level == 3:
            # Primeiro aplica nível 2 no código original
            inner = self._remove_comments(code)
            inner = self._rename_vars(inner)
            inner = self._encode_strings(inner)
            inner = self._encode_numbers(inner)
            inner = self._add_junk_code(inner, density=4)
            # Depois envolve em bytecode wrapper
            return self._wrap_bytecode_style(inner)

        # Nível 1 e 2
        result = self._remove_comments(code)
        result = self._rename_vars(result)
        result = self._encode_strings(result)

        if level >= 2:
            result = self._encode_numbers(result)
            result = self._add_junk_code(result, density=3)

        return result

    def get_stats(self, original: str, obfuscated: str) -> dict:
        """Retorna estatísticas da ofuscação."""
        orig_size = len(original)
        obf_size = len(obfuscated)
        increase = round(((obf_size - orig_size) / max(orig_size, 1)) * 100, 1)
        return {
            "original_size": orig_size,
            "obfuscated_size": obf_size,
            "increase": increase,
            "vars_renamed": self._stats["vars_renamed"],
            "strings_encoded": self._stats["strings_encoded"],
            "junk_added": self._stats["junk_added"],
        }
