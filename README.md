Projeto do NASA Space Apps. Este repositório traz a primeira camada de dados: o clima local da Cratera Jezero, medido pelo rover Perseverance (instrumento MEDA).

## O que o ETL faz

1. **Lê** 3 CSVs do nível derived do MEDA (sol 539): pressão (PS), umidade (RHS) e infravermelho (TIRS).
2. **Limpa** valores inválidos e linhas repetidas.
3. **Transforma** 1 medição por segundo em 1 por minuto (mediana) e une os 3 sensores.
4. **Salva** `output/meda_jezero.xlsx` com 2 abas:
   - `base_tratada`: uma linha por minuto.
   - `dados_chave`: mínimo, média e máximo por hora solar local.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/etl_meda.py
```

Baixe os CSVs (link abaixo) e coloque em `raw/`.

## Estrutura

```
raw/      CSVs originais da NASA (não vão para o Git)
src/      etl_meda.py
output/   meda_jezero.xlsx
docs/     documento do projeto
```

## Limitações

- Os dados cobrem cerca de 13 das 24,7 horas da sol, porque o rover alterna as horas de medição.
- `temp_sensor_c` é a temperatura do sensor de umidade, não a temperatura oficial do ar.
- Os valores de infravermelho são irradiâncias, não temperatura de superfície.
- As unidades (Pa, %, K, W/m²) devem ser confirmadas nos `.xml` de cada CSV.

## Fontes

- Onde baixamos os CSVs (sol 539): https://atmos.nmsu.edu/PDS/data/PDS4/Mars2020/mars2020_meda/data_derived_env/sol_0420_0539/sol_0539/
- Página de dados do MEDA no PDS: https://pds-atmospheres.nmsu.edu/data_and_services/atmospheres_data/PERSEVERANCE/meda.html
- Readme do release (níveis de dados e regras de qualidade): https://pds.nasa.gov/data/pds4/releases/atmos/mars2020_meda-20260811/readme.txt
- Artigo do instrumento (Rodriguez-Manfredi et al., 2021): https://link.springer.com/content/pdf/10.1007%2Fs11214-021-00816-9.pdf
- NASA NTRS (MEDA): https://ntrs.nasa.gov/citations/20210014064