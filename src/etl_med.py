'''
Extração de dados do Meda, estação meterológica do rover Perseverance da cratera Jazero - Marte.

O script abaixo é um etl simples, que ler os CSVs públicos da NASA (na pasta raw), limpa, transforma e salvo para usarmos 

Glossário de alguns termos: 
    sol - equivalente a um dia em Marte. "sol 539" significa o 539° dia de missão
    MEDA - são os sensores de clima do rover
    SCLK - relógio da nave, em segundos. Serve para agruparmos os minutos
    LTST - uma hora solar em Marte
    PS - sensor de presão 
    RHS - sensor de umidade
    TIRS - sensor de infravermelho 
'''
import re
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font

ARQUIVOS_ENTRADA = Path('raw')
ARQUIVO_SAIDA = Path('output/meda_jezero.xlsx')

VALOR_INVALIDO = VALOR_INVALIDO = 9999999999        # código usado pela NASA usa para campos "sem dado"
SEGUNDOS_POR_MINUTOS = 60
ZERO_ABSOLUTO_KELVIN = 273.15 # converte kelvin pra celsius

SOL_MINIMA_CONFIAVEL = {"rhs": 63}

# Para cada sensor: {nome da coluna na NASA: nome que usamos no projeto}
COLUNAS_POR_SENSOR = {
    "ps":   {"PRESSURE": "pressao_pa"},
    "rhs":  {"LOCAL_RELATIVE_HUMIDITY": "umidade_rel_pct",
            "HUMIDITY_LOCAL_TEMP": "temp_sensor_k"},
    "tirs": {"DOWNWARD_LW_IRRADIANCE": "ir_descendente",
            "UPWARD_LW_IRRADIANCE": "ir_ascendente"},
}

def identificar_sol_e_sensor(caminho: Path):
    """Descobre sol e sensor pelo nome do arquivo.
    Ex.: 'WE__0539___DER_PS___P01.CSV' -> (539, 'ps')"""
    nome = caminho.name.lower()
    achou_sol = re.search(r"we__(\d{4})", nome)
    achou_sensor = re.search(r"_der_([a-z0-9]+)", nome)
    sol = int(achou_sol.group(1)) if achou_sol else None
    sensor = achou_sensor.group(1) if achou_sensor else None
    return sol, sensor

def limpar(tabela: pd.DataFrame) -> pd.DataFrame:
    """Troca o valor inválido por vazio e remove linhas repetidas."""
    tabela = tabela.mask(tabela == VALOR_INVALIDO)
    return tabela.drop_duplicates()


def resumir_por_minuto(tabela: pd.DataFrame, colunas: list) -> pd.DataFrame:
    """O rover mede 1x por segundo. Agrupamos por minuto e usamos a MEDIANA
    (ela não se deixa enganar por picos de ruído)."""
    tabela["minuto"] = tabela["SCLK"] // SEGUNDOS_POR_MINUTOS
    regras = {coluna: "median" for coluna in colunas}
    regras["LTST"] = "first"        # guarda a hora local do 1º segundo do minuto
    return tabela.groupby("minuto").agg(regras).reset_index()

def processar_arquivo(caminho: Path):
    """Lê UM csv e devolve a tabela por minuto (ou None se não serve)."""
    sol, sensor = identificar_sol_e_sensor(caminho)

    sensor_desconhecido = sensor not in COLUNAS_POR_SENSOR
    antes_da_sol_confiavel = sol is not None and sol < SOL_MINIMA_CONFIAVEL.get(sensor, 0)
    if sol is None or sensor_desconhecido or antes_da_sol_confiavel:
        return None

    nomes_novos = COLUNAS_POR_SENSOR[sensor]
    tabela = limpar(pd.read_csv(caminho))
    tabela = tabela[["SCLK", "LTST", *nomes_novos]].rename(columns=nomes_novos)

    por_minuto = resumir_por_minuto(tabela, list(nomes_novos.values()))
    por_minuto.insert(0, "sol", sol)
    return por_minuto

def juntar_sensores(tabelas: list) -> pd.DataFrame:
    """Une pressão, umidade e infravermelho na mesma linha (mesmo sol e minuto)."""
    base = pd.concat(tabelas).groupby(["sol", "minuto"]).first().reset_index()

    # Hora local = os 2 dígitos antes dos minutos. Ex.: "0539 14:30:00" -> 14
    base["hora_local"] = base["LTST"].str[-8:-6].astype(int)
    base = base.rename(columns={"LTST": "ltst"})

    if "temp_sensor_k" in base:
        base["temp_sensor_c"] = (base["temp_sensor_k"] - ZERO_ABSOLUTO_KELVIN).round(2)
        base = base.drop(columns="temp_sensor_k")

    return base.sort_values("minuto")

def criar_perfil_por_hora(base: pd.DataFrame) -> pd.DataFrame:
    """Para cada hora do dia marciano: mínimo, média e máximo de cada medida."""
    medidas = [c for c in base.columns if c not in ("sol", "minuto", "ltst", "hora_local")]
    perfil = base.groupby("hora_local")[medidas].agg(["min", "mean", "max"]).round(2)
    perfil.columns = [f"{medida}_{estatistica}" for medida, estatistica in perfil.columns]
    return perfil.reset_index()

def formatar_excel(caminho: Path):
    """Fonte Arial, cabeçalho em negrito, colunas largas e 1ª linha congelada."""
    planilha = load_workbook(caminho)
    for aba in planilha:
        for linha in aba.iter_rows():
            for celula in linha:
                celula.font = Font(name="Arial", size=10, bold=(celula.row == 1))
        for coluna in aba.columns:
            aba.column_dimensions[coluna[0].column_letter].width = 22
        aba.freeze_panes = "A2"
    planilha.save(caminho)

def salvar_excel(base: pd.DataFrame, perfil: pd.DataFrame):
    ARQUIVO_SAIDA.parent.mkdir(exist_ok=True)
    with pd.ExcelWriter(ARQUIVO_SAIDA, engine="openpyxl") as escritor:
        base.to_excel(escritor, sheet_name="base_tratada", index=False)
        perfil.to_excel(escritor, sheet_name="dados_chave", index=False)
    formatar_excel(ARQUIVO_SAIDA)

def main():
    arquivos_csv = sorted(p for p in ARQUIVOS_ENTRADA.iterdir() if p.suffix.lower() == ".csv")
    tabelas = [processar_arquivo(p) for p in arquivos_csv]
    tabelas = [t for t in tabelas if t is not None]
    if not tabelas:
        raise SystemExit(f"Nenhum CSV válido em {ARQUIVOS_ENTRADA}/")

    base = juntar_sensores(tabelas)
    perfil = criar_perfil_por_hora(base)
    salvar_excel(base, perfil)
    print(f"OK -> {ARQUIVO_SAIDA} | base: {len(base)} linhas | perfil: {len(perfil)} linhas")

if __name__ == "__main__":
    main()
