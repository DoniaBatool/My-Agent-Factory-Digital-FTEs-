**Wire Spec-KitPlus into Claude via MCP**

To let Claude Code actually *run* Spec-KitPlus commands, you will set up an MCP server with prompts present in .claude/commands. Each command here will become a prompt in the MCP server.

**4.1 Install SpecKitPlus, Create an MCP Server**

1. uv init specifyplus \<project\_name\>  
2. Create your Consitution  
3. Add Anthropic's official MCP Builder Skill   
4. Using SDD Loop (Specify, Plan, Tasks, Implement) you will  set up an MCP server with prompts present in .claude/commands  
5. Use these as part of your prompt instructions in specify: \`We have specifyplus commands on @.claude/commands/\*\* Each command takes user input and updates its prompt variable before sending it to the agent. Now you will use your mcp builder skill and create an mcp server where these commands are available as prompts. Goal: Now we can run this MCP server and connect with any agent and IDE.  
6. Test the MCP server

**4.2 Register with Claude Code**

Add the server to your Claude Code config (usually .mcp.json at your project root):

{  
  "mcpServers": {  
    "spec-kit": {  
      "command": "spec-kitplus-mcp",  
      "args": \[\],  
      "env": {}  
    }  
  }  
}  
**Success:**

* After running MCP Server and connecting it with Claude Code now you can have the same commands available as MCP prompts.

