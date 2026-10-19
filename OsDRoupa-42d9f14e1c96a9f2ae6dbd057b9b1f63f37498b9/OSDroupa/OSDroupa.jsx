
import {ReflexEvent,applyEventActions,isTrue} from "$/utils/state"
import {ColorModeContext,addEvents} from "$/utils/context"
import {Fragment,memo,useCallback,useContext,useEffect} from "react"
import {jsx} from "@emotion/react"
import {IconButton as RadixThemesIconButton} from "@radix-ui/themes"








export const Cond_comp_ebf386315eb9eecf7e3ce0b81790a2f1_a7f7aaa5 = memo(({children}) => {
    const { resolvedColorMode } = useContext(ColorModeContext)



    return(
        ((resolvedColorMode?.valueOf?.() === "light"?.valueOf?.())?(children?.at?.(0)):(children?.at?.(1)))
    )
});
Cond_comp_ebf386315eb9eecf7e3ce0b81790a2f1_a7f7aaa5.displayName = "Cond";

export const Iconbutton_iconbutton_72e30e9253eb12d4551f53265bdecab0_a7f7aaa5 = memo(({children}) => {
    const { toggleColorMode } = useContext(ColorModeContext)
const on_click_dedd885ce47a15c1666b026c014cf563 = useCallback(((_e) => (toggleColorMode(_e))), [addEvents, ReflexEvent, toggleColorMode])



    return(
        jsx(RadixThemesIconButton,{css:({ ["padding"] : "6px", ["position"] : "fixed", ["top"] : "2rem", ["right"] : "2rem", ["background"] : "transparent", ["color"] : "inherit", ["zIndex"] : "20", ["&:hover"] : ({ ["cursor"] : "pointer" }) }),onClick:on_click_dedd885ce47a15c1666b026c014cf563},children)
    )
});
Iconbutton_iconbutton_72e30e9253eb12d4551f53265bdecab0_a7f7aaa5.displayName = "IconButton";
