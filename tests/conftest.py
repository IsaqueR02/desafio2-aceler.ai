"""Fixtures compartilhadas dos testes.

`edstats_wide` reproduz o schema real do World Bank EdStats (formato wide):
colunas de identificação + uma coluna por ano, incluindo valores ausentes,
para exercitar limpeza e tratamento como no arquivo verdadeiro.
"""
from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def edstats_wide() -> pd.DataFrame:
    """Amostra mínima no layout do EdStatsData.csv (com lacunas e coluna vazia)."""
    return pd.DataFrame(
        {
            "Country Name": ["Brazil", "Finland", "India"],
            "Country Code": ["BRA", "FIN", "IND"],
            "Indicator Name": [
                "Gasto público em educação (% do PIB)",
                "Gasto público em educação (% do PIB)",
                "Gasto público em educação (% do PIB)",
            ],
            "Indicator Code": ["SE.XPD.TOTL.GD.ZS"] * 3,
            "2000": [4.0, 6.0, 3.0],
            "2005": [None, 6.5, None],   # lacunas a serem tratadas
            "2010": [5.5, 7.0, 3.8],
            "Unnamed: 5": [None, None, None],  # coluna espúria típica do EdStats
        }
    )


@pytest.fixture
def edstats_long(edstats_wide: pd.DataFrame) -> pd.DataFrame:
    """Versão long já derretida (import tardio p/ evitar dependência circular)."""
    from src.tratamento import limpar_e_derreter

    # Remove a coluna espúria antes, como faz a coleta real.
    limpo = edstats_wide.loc[:, ~edstats_wide.columns.str.startswith("Unnamed")]
    return limpar_e_derreter(limpo)
