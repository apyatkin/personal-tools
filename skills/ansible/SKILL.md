---
name: ansible
description: Use when working with Ansible — playbooks, inventory, ansible-vault, roles, or any Ansible-related task
---

# Ansible

## Company Context

To get company-specific Ansible settings:

1. Read `~/Library/hat/state.json` to get `active_company`
2. Read `~/Library/hat/companies/<active_company>/config.yaml`
3. Use `ssh` section — reads `keys` for SSH access to managed hosts

SSH keys should already be loaded by `hat on`.

## Commands

### Playbooks

```bash
ansible-playbook -u <user> -i inventory/<file> <playbook>.yaml
ansible-playbook --vault-password-file .ansible_vault_pass <playbook>.yaml
ansible-playbook --check --diff <playbook>.yaml       # dry run (safe)
ansible-playbook -l <host-pattern> <playbook>.yaml    # limit to hosts
ansible-playbook -vvv <playbook>.yaml                 # verbose debug
```

### Vault

```bash
ansible-vault encrypt <file>                          # encrypt file
ansible-vault decrypt <file>                          # decrypt file
ansible-vault view <file>                             # view encrypted file
ansible-vault edit <file>                             # edit in-place
ansible-vault encrypt_string '<value>' --name '<var>' # encrypt single value
```

### Linting

```bash
ansible-lint --profile min                            # lint playbooks
ansible-lint <playbook>.yaml                          # lint single file
```

### Ad-hoc

```bash
ansible <host-pattern> -i inventory/<file> -m ping    # test connectivity
ansible <host-pattern> -i inventory/<file> -m shell -a "uptime"  # run command
```

## Runbooks

### Run with Vault

1. Ensure vault password file exists: `.ansible_vault_pass` or prompted
2. Run: `ansible-playbook --vault-password-file .ansible_vault_pass -i inventory/<file> <playbook>.yaml`

### Limit to Specific Hosts

1. Check inventory: `ansible-inventory -i inventory/<file> --list`
2. Run with limit: `ansible-playbook -l <host-or-group> -i inventory/<file> <playbook>.yaml`

### Dry-Run (Check Mode)

1. Run: `ansible-playbook --check --diff -i inventory/<file> <playbook>.yaml`
2. Review the diff output — shows what WOULD change
3. Note: not all modules support check mode perfectly

### Debug Connection Issues

1. Test ping: `ansible <host> -i inventory/<file> -m ping`
2. If fails, add verbosity: `ansible <host> -i inventory/<file> -m ping -vvv`
3. Check SSH key, user, and host in inventory
4. Verify SSH agent has the right key: `ssh-add -l`
