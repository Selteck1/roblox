-- Example ModuleScript in ReplicatedStorage.
local ExampleModule = {}

function ExampleModule.greet(playerName: string): string
    return "Hello, " .. playerName .. "!"
end

return ExampleModule
