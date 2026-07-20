# Custom Workspace Rules for Viral Formula Studio

Always apply the following reasoning process and response structure before generating or modifying any code in this project.

### Mandatory Reasoning Process (do this BEFORE generating any code):

1. Perform mental simulation and static analysis of the proposed changes.
2. Consider edge cases, state changes, performance implications, interactions with other parts of the system, and potential regressions.
3. Analyze both direct and indirect impacts of the modification.

### Response Structure (ALWAYS follow this exact structure):

### 1. Análise e Raciocínio
- Onde (Where): Specify exactly which files, functions, classes, or modules will be modified.
- Como (How): Explain the technical approach that will be used.
- Por que (Why): Justify the decision. Mention alternatives considered and why they were not chosen.
- Impacto Específico: Direct and immediate effects of this change.
- Impacto Inespecífico / Efeitos Colaterais: Indirect, long-term, or non-obvious consequences (performance, maintainability, coupling, future changes, etc.).

### 2. Testes Mentais e Estáticos Realizados
List the validations, simulations, and static analyses you performed mentally before proposing the solution. Include important edge cases considered and how they are handled.

### 3. Mudanças Propostas (Commented Diff)
Show the proposed changes using a clear commented diff format. Add comments explaining the reason for relevant modifications.

Use this format:
```diff
diff --git a/path/to/file.py b/path/to/file.py
index abc1234..def5678 100644
--- a/path/to/file.py
+++ b/path/to/file.py
@@ -45,6 +45,12 @@ def some_function():
     existing_code()
+
+    # Reason: [explain why this change was made]
+    new_code_here()
+
     more_existing_code()
```
