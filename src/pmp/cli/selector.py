from typing import Sequence, TypeVar


T = TypeVar("T")


class Selector:
    
    def confirm(self, message):
    	confirmation = input(f"{message} (y, n) ").strip().lower()
    	if confirmation == "y":
    		return True
    	return False

    def choose(
        self,
        items: Sequence[T],
    ) -> T:

        if not items:
            raise ValueError(
                "Nenhuma opção disponível."
            )

        if len(items) == 1:
            return items[0]


        self._display(items)

        index = self._ask_index(
            len(items)
        )

        return items[index]


    def _display(
        self,
        items: Sequence[T],
    ) -> None:

        for number, item in enumerate(
            items,
            start=1,
        ):
            name = getattr(item, "name", None) or getattr(item, "title", None)
            item_type = type(item).__name__
            
            print(
                f"{number} - {item_type}: {name}"
            )


    def _ask_index(
        self,
        size: int,
    ) -> int:
    	
    	attempts = 3
    	
    	while attempts:
    		try:
    			value = int(
    				input(
    					"Escolha (digite o numero): "
    				)
    			)
    			
    			if 1 <= value <= size:
    			     return value - 1
    		
    		except ValueError:
    			pass
    		
    		attempts -= 1
    		
    		print(
                f"Escolha inválida ({attempts} tentativas restantes)"
            )
                                          	
    	raise ValueError("Nenhuma musica escolhida")                       