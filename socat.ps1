$socketName = $args[0]
$message = $args[1]

$npipeClient = new-object System.IO.Pipes.NamedPipeClientStream('.', $socketName, [System.IO.Pipes.PipeDirection]::InOut, [System.IO.Pipes.PipeOptions]::None, [System.Security.Principal.TokenImpersonationLevel]::Impersonation)

$pipeReader = $pipeWriter = $null
try {
    $npipeClient.Connect()
    $pipeReader = new-object System.IO.StreamReader($npipeClient)
    $pipeWriter = new-object System.IO.StreamWriter($npipeClient)
    $pipeWriter.AutoFlush = $true

    $pipeWriter.WriteLine($message)
    ($data = $pipeReader.ReadLine())
}
catch {
    "An error occurred that could not be resolved."
}
finally {
    $npipeClient.Dispose()
}