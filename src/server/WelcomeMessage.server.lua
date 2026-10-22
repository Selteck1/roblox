-- Example server script. Run the place in Roblox Studio to see messages in Output.
local Players = game:GetService("Players")

Players.PlayerAdded:Connect(function(player)
    print("Welcome, " .. player.Name .. "!")
end)
