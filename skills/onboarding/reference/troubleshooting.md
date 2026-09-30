# Troubleshooting a connection that stopped working

For a connection that validated before and now fails. The goal is the cause, confirmed with
evidence, and a fix the customer applies; Monte Carlo usually needs no change. Everything here
reads metadata, audit logs or validation results, never a secret's value (output-modes: rules
for every command).

## Order of checks

1. **Validate what exists.** `validate_connection(connection_id)`, then the credentials alone
   with the matching `validate_<store>_credentials` (same arguments as the create, plus
   `deployment_id`). Read the runs with `get_validation_run` and quote each failing
   validation's `friendly_message` and `resolution`.
2. **Compare with a healthy connection on the same agent** (`list_connections`, same
   `deployment_id`). If it passes, the agent and its network are fine and the problem is this
   connection's secret, grant or database. If every connection on the agent fails, look at the
   agent: its stack, VPC, NAT, or a recent upgrade.
3. **For a self-hosted reference, check the agent's access to each secret first.** It is the
   most common cause after a change and the cheapest to confirm: the IAM policy simulator on the
   agent's execution role, one decision per secret (`ResourceSpecificResults`, see output-modes).
   `implicitDeny` on the failing secret and `allowed` on the working one confirms it.
   GCP and Azure: the service account's IAM on the secret, the Key Vault access policy or RBAC.
4. **Find what changed since it last worked.** CloudTrail (or the cloud's audit log) between
   the last good time and the first failure, as fixed UTC timestamps: `PutRolePolicy`,
   `DeleteRolePolicy`, `DetachRolePolicy`, security-group changes, `ModifyDBInstance`,
   `PutSecretValue` / `UpdateSecret` / `RotateSecret`, stack updates. Ask the customer when it
   last worked and when it first failed rather than guessing.
5. **Fix on the side that changed**, with a reviewed edit: list the role's policies (grants are
   often split across several), back up the policy, edit with `jq`, `diff`, then apply; or
   restore the security-group rule; or point the credentials at a recreated secret's new ARN
   (`update_<store>_credentials`). Then re-run step 1. If the change came from Terraform or
   CloudFormation, fix it there, or the next apply reverts it.
6. **Escalate with ids** when none of the above explains it: the connection id and the failing
   validation run id, for Monte Carlo support, who can see the agent's unredacted errors.

## Signals and what they do not mean

| Validation shows | Most likely | Confirm with |
|---|---|---|
| Credentials warning "invalid or unreachable" + "Could not connect", a healthy connection on the same agent | The agent can't read this secret: IAM grant removed, customer-managed KMS key, secret resource policy | Simulator per secret; `describe-secret` (`KmsKeyId`); `get-resource-policy`; CloudTrail |
| Same, and the secret's ARN suffix changed | The secret was deleted and recreated | `describe-secret`; update the credentials to the new ARN |
| "Could not connect", credentials valid, slow failure | Network path: security group, route, NAT, database moved or stopped | The database's inbound rules for the agent's security group; its status and endpoint |
| Connects but fails **Tables** | Grants revoked, schemas moved, or the database has no tables | The user's grants per the connector's docs page |
| Every connection on the agent fails | The agent itself | Stack events, the agent's subnets and NAT, `get_deployment` |

- **IMPORTANT: the agent's own logs are not a diagnostic source.** It redacts error messages
  (`__redacted__`); only an exception type such as `ValueError` is visible, and the same type is
  raised for unreadable secrets, parse errors and connection failures. Don't send the customer
  to them, and don't infer a cause from the exception type.
- **IMPORTANT: a secret that didn't change is not a JSON problem.** Check its metadata
  (`LastChangedDate`, versions) before suggesting its content is wrong, and never ask to see it.
- NEVER change the connection, warehouse or credentials in Monte Carlo to fix a cloud-side
  cause; only re-point credentials when the secret's ARN itself changed.
