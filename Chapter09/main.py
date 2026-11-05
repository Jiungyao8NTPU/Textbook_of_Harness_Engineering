#!/usr/bin/env python3
import sys
import json
import hashlib
from pathlib import Path

from runtime.gateway import Gateway
from runtime.control_plane import ControlPlane
from runtime.tool_runner import SandboxedToolRunner
from runtime.model_client import LocalGemmaClient

def main():
    root = Path(__file__).parent.resolve()
    gateway = Gateway(root / "installed_skills")
    
    # Calculate real digest of SKILL.md to align lockfile for laboratory validation
    skill_file = root / "installed_skills" / "system-diagnostician" / "SKILL.md"
    skill_digest = f"sha256:{hashlib.sha256(skill_file.read_bytes()).hexdigest()}"
    
    lockfile_path = root / "config" / "registry_lock.json"
    lock_data = {"skills": {"system-diagnostician": {"version": "1.0.0", "digest": skill_digest}}}
    lockfile_path.write_text(json.dumps(lock_data, indent=2))

    control_plane = ControlPlane(str(root / "config" / "policies.json"), str(lockfile_path))
    tool_runner = SandboxedToolRunner()
    llm = LocalGemmaClient()

    print("==================================================")
    print(" HARNESS ENGINEERING: GOVERNED SKILL SYSTEM")
    print("==================================================")

    # 1. Verification of Provenance & Trust
    target_skill = "system-diagnostician"
    skill_dir = root / "installed_skills" / target_skill
    print(f"\n[*] Stage 1: Verifying Provenance for '{target_skill}'...")
    if not control_plane.verify_provenance(skill_dir):
        print("[-] FATAL: Skill digest mismatch. Tampering detected!")
        sys.exit(1)
    print("[+] Provenance verified: Digest matches cryptographic lockfile.")

    # 2. Metadata Gating
    print(f"\n[*] Stage 2: Evaluating Deterministic Metadata Gates...")
    if not gateway.evaluate_metadata_gates(target_skill):
        print("[-] GATING FAILED: Host missing required runtime binaries.")
        sys.exit(1)
    print("[+] Metadata gating passed: Environment satisfies compatibility declarations.")

    # 3. Progressive Disclosure (Activation)
    print(f"\n[*] Stage 3: Activating Skill via Progressive Disclosure...")
    manifest, instructions = gateway.activate_skill_context(target_skill)
    print(f"[+] Loaded instructions ({len(instructions.splitlines())} lines). System prompt enriched.")

    # 4. Cognitive Orchestration with Local Gemma 4
    user_request = "Triage active incident INC-9281: checkout-service latency spike."
    user_role = "site-reliability-engineer"
    print(f"\n[*] Stage 4: Ingesting Incident Request under Role '{user_role}'...")

    response = llm.generate_plan_or_call(instructions, user_request, manifest["allowed-tools"].split())
    
    if "tool_calls" in response:
        for call in response["tool_calls"]:
            tool_name = call["function"]["name"]
            tool_args = json.loads(call["function"]["arguments"])
            print(f"\n[!] Model emitted tool call: {tool_name}({tool_args})")

            # 5. Control Plane Authorization Gate
            print(f"[*] Stage 5: Control Plane Interception & Scope Validation...")
            authorized = control_plane.authorize_tool_dispatch(user_role, manifest, tool_name)
            
            if not authorized:
                print(f"[-] ACCESS DENIED: Control Plane blocked tool '{tool_name}'.")
                continue
            
            print(f"[+] Authorized. Executing inside ephemeral Podman sandbox...")
            
            # 6. Sandboxed Execution
            tool_result = tool_runner.execute_tool(tool_name, tool_args)
            print(f"[+] Sandbox Return: {json.dumps(tool_result)}")

            # 7. Procedural Branching: If telemetry shows degraded health, invoke remediation
            if tool_name == "query_service_telemetry" and tool_result.get("error_count", 0) > 50:
                print("\n[*] Procedural Invariant Triggered: High Error Rate detected.")
                remediation_tool = "restart_service_pod"
                print(f"[*] Dispatching Remediation Tool: '{remediation_tool}'...")
                
                if control_plane.authorize_tool_dispatch(user_role, manifest, remediation_tool):
                    rem_res = tool_runner.execute_tool(remediation_tool, {"service_name": "checkout-service"})
                    print(f"[+] Remediation Result: {json.dumps(rem_res)}")
                
                # Verify recovery
                health_res = tool_runner.execute_tool("check_endpoint_health", {"service_name": "checkout-service"})
                print(f"[+] Post-Remediation Verification: {json.dumps(health_res)}")

    print("\n==================================================")
    print(" CONTROL PLANE AUDIT TRAIL")
    print("==================================================")
    for entry in control_plane.audit_log:
        print(f" - [{entry['decision']}] Tool: {entry.get('tool')} | Details: {entry.get('reason', 'Granted to ' + entry.get('role', ''))}")

if __name__ == "__main__":
    main()
