import streamlit as st


def load_css():

    st.markdown(

    """

<style>


.driver-card{

    background:
    linear-gradient(
    180deg,
    #111827,
    #05070c
    );

    border-radius:14px;

    padding:18px;

    text-align:center;

    height:420px;

}


.position{

    font-size:22px;

    font-weight:700;

    margin-bottom:10px;

}


.driver-image{

    height:250px;

    max-width:220px;

    object-fit:contain;

}


.driver-name{

    font-size:18px;

    font-weight:700;

    margin-top:15px;

}


.driver-team{

    color:#9ca3af;

    margin-top:5px;

}


.driver-points{

    font-size:22px;

    font-weight:700;

    margin-top:15px;

}



.small-row{


display:flex;

align-items:center;

padding:15px;

border-bottom:1px solid #262626;


}



.avatar{

width:70px;

height:70px;

border-radius:50%;

object-fit:cover;

margin-right:25px;


}



.small-pos{

width:50px;

font-weight:700;

}



.small-info{

flex:1;

display:flex;

flex-direction:column;


}



.small-info span{

color:#9ca3af;

font-size:13px;

}



.small-points{

font-weight:700;

}



</style>


    """,

    unsafe_allow_html=True

    )