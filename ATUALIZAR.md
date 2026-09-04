# Atualizar esta skill na sua máquina

O `git pull` sozinho não basta: o arquivo ponteiro vive fora do repositório
(em `~/.claude/skills/`) e o `.env` não é versionado.

**Cole o bloco abaixo no seu Claude Code**, na pasta do projeto, e siga o que ele pedir.

---

```
Preciso atualizar a skill blog-mk-payload nesta máquina. O git pull sozinho não
resolve, porque o arquivo ponteiro vive fora do repositório e o .env não é
versionado.

CONTEXTO DO QUE MUDOU (para você entender o que está instalando):
- A skill ganhou um "Modo LinkedIn": ao terminar um artigo ela gera
  output/<slug>/linkedin.md e posta na página da metaKosmos via webhook do Make.
- O artigo do blog passou a ser publicado AO VIVO por padrão, não mais como
  rascunho. Não existe mais revisão humana antes do público.
- A ordem passou a ser: artigo ao vivo primeiro, post no LinkedIn depois.

FAÇA NESTA ORDEM:

1. Localize a pasta onde o repositório blog-skill-payload está clonado nesta
   máquina (o remote é github.com/patrick-metakosmos/blog-skill-payload).
   Se não achar, me pergunte o caminho.

2. Antes de puxar, verifique se há trabalho local não commitado com git status.
   Se houver, me mostre o que é e pergunte o que fazer. Não descarte nada.

3. git pull. Se der conflito, me mostre antes de resolver.

4. Copie o arquivo ponteiro-skill.md do repositório para
   ~/.claude/skills/blog-mk-payload/SKILL.md, trocando SOMENTE a linha que
   começa com "**BASE:**" pelo caminho real onde o repositório está clonado
   nesta máquina. Não reescreva nem resuma o resto do arquivo: ele carrega as
   correções de rota e as regras de publicação, e uma versão encurtada faz a
   skill trabalhar com regra velha.

5. Adicione a variável LINKEDIN_WEBHOOK_URL no arquivo .env do repositório.
   Peça o valor para mim. Essa URL é credencial: quem tem ela posta na página
   da empresa. Nunca commite esse valor, nunca escreva ele em nenhum arquivo
   versionado, e confirme que .env está no .gitignore.

6. VERIFIQUE sem publicar nada. Rode só comandos que não postam:
     python scripts/payload_publish.py --list
     python scripts/linkedin_publish.py --list
   e confirme que os scripts rodam sem erro de import.
   NÃO rode payload_publish.py nem linkedin_publish.py sem --dry-run durante
   esta instalação: os dois publicam ao vivo e são irreversíveis.
   No Windows, prefixe os comandos com PYTHONIOENCODING=utf-8 se os acentos
   saírem quebrados.

7. Leia references/linkedin-post.md e o SKILL.md do repositório, e me faça um
   resumo curto do que muda na minha rotina de escrever artigo, destacando:
   - que a auditoria (audit_artigo.py) virou a única checagem antes do público
     e que nenhum bloqueador dela pode ser relevado
   - que o LinkedIn não deduplica e rodar duas vezes cria dois posts
   - o que é a trava .linkedin-posted.json e quando ela aparece

8. Se quiser ver um exemplo pronto do fluxo completo, o artigo
   llms-txt-dinamico-catalogo foi publicado como piloto e está no ar.
   Mas a pasta output/ não é versionada, então ela não veio no pull.
```

---

## Se você preferir fazer na mão

1. `git pull`
2. Copiar `ponteiro-skill.md` para `~/.claude/skills/blog-mk-payload/SKILL.md`,
   trocando só a linha `**BASE:**` pelo caminho do seu clone.
3. Adicionar `LINKEDIN_WEBHOOK_URL=` no seu `.env` e pedir o valor ao Patrick.
4. Conferir que roda: `python scripts/linkedin_publish.py --list`

## Depois de todo `git pull`

Confira se o `ponteiro-skill.md` mudou. Se mudou, recopie para
`~/.claude/skills/blog-mk-payload/SKILL.md`. É o arquivo que carrega as regras
de publicação, e uma cópia velha faz a skill trabalhar com regra antiga.
