.PHONY: governance security test lint

governance:
	python scripts/validate_governance.py

security:
	python scripts/check_forbidden_patterns.py .

lint: governance security

# 业务工程创建后，由各子项目补充真实命令。
test: lint
	@echo "Governance checks passed. Application test commands are added during bootstrap issues."
