# Revisão de Código

Faça uma revisão completa do código deste projeto nas 5 dimensões abaixo. Para cada problema encontrado, classifique como **crítico**, **possivelmente preocupante** ou **sugestão**, identifique o processo/arquivo afetado e dê uma sugestão concreta do que fazer.

---

## #1 Segurança

Avalie:
- Informações privadas publicamente expostas
- Autenticação: se existe e se cobre todas as páginas que deveriam tê-la
- Tokens, senhas e variáveis privadas hardcoded no código (devem estar em variáveis de ambiente)
- Falhas que permitam exploração do sistema: SQL injection, XSS, command injection, CSRF, path traversal, e outros do OWASP Top 10
- Dados sensíveis commitados no repositório (arquivos .env, chaves, planilhas com dados reais)

## #2 Performance

Avalie:
- Carregamento ineficiente de dados que possa estourar memória (carregar tudo de uma vez sem paginação ou streaming)
- Queries ou operações com complexidade exponencial ou que não escalam
- Suporte a múltiplos usuários simultâneos
- Possíveis vazamentos de memória (conexões não fechadas, caches sem limite, listeners não removidos)
- Gargalos que aparecerão ao escalar: operações sem cache, N+1 queries, processamento síncrono onde deveria ser assíncrono

## #3 Erros

Avalie:
- Fluxos normais de uso que podem lançar exceções não tratadas
- Ausência de try/catch onde erros são prováveis (I/O, rede, parsing, divisão por zero)
- Erros sem log que dificultarão diagnóstico em produção
- Problemas que só aparecem em produção mas não localmente (paths relativos, variáveis de ambiente faltando, encoding, permissões de arquivo)
- Incompatibilidades de versão de dependências

## #4 Testes

- Verifique se existe arquivo de testes no projeto. Se não existir, crie um.
- Rode os testes e reporte quais passam e quais falham.
- Identifique funcionalidades críticas que não têm cobertura de teste e adicione-as ao arquivo de testes.
- Reporte o resultado final: X/Y testes passando.

## #5 Deploy

Se nenhum problema crítico foi encontrado nas etapas anteriores:
- Verifique se o código local está sincronizado com o repositório remoto (git status, git log vs origin)
- Verifique se requirements/dependencies estão declarados e com versões fixas
- Verifique se configurações de ambiente (variáveis, arquivos de config) estão documentadas

---

## Formato do Relatório

Ao final, apresente:
1. Uma seção por dimensão (#1 a #5) com os problemas encontrados, cada um com: criticidade, processo/arquivo afetado e sugestão
2. Um **Resumo Executivo** em tabela com todos os problemas e criticidades
3. Uma linha final dizendo se o código está pronto para deploy ou o que precisa ser resolvido primeiro
