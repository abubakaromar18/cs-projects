defmodule BankActors.MixProject do
  use Mix.Project

  def project do
    [
      app: :bank_actors,
      version: "0.1.0",
      elixir: "~> 1.14",
      start_permanent: Mix.env() == :prod,
      deps: []
    ]
  end

  # The application callback starts the supervision tree automatically.
  def application do
    [
      extra_applications: [:logger],
      mod: {BankActors.Application, []}
    ]
  end
end
