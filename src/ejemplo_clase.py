class Personaje:
    def __init__(self, vida_inicial, mana_inicial):
        self.vida = vida_inicial
        self.mana = mana_inicial

    def quitar_vida(self, vida_a_quitar):
        self.vida = self.vida - vida_a_quitar

juan = Personaje(100, 20)
roberto = Personaje(100, 20)

juan.quitar_vida(20)
juan.quitar_vida(20)
juan.quitar_vida(20)

print(juan.vida)
print(juan.mana)

print(roberto.vida)
print(roberto.mana)
