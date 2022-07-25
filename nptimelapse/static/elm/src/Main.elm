module Main exposing (..)


import Browser
import Html exposing (Html, button, div, text, br)
import Html.Attributes exposing (class)
import Html.Events exposing (onClick)
import SingleSlider exposing (SingleSlider)
import Svg exposing (Svg, svg, rect, circle)
import Svg.Attributes exposing (x, y, width, height, viewBox, fill, r, cy, cx)
import Json.Decode exposing (Decoder, decodeValue, field, float, int, keyValuePairs, list)
import Dict
import Time


-- CONSTANTS


starRadius = 0.1
mapPadding = 0.5


first : ( a, b ) -> a
first ( a, b ) = a


second : ( a, b ) -> b
second ( a, b ) = b


-- COLORS


type alias Color =
  { r : Int
  , g : Int
  , b : Int
  }


baseColors : Int -> Color
baseColors i =
  case i of
    0 -> Color 0 0 255
    1 -> Color 0 255 255
    2 -> Color 0 255 0
    3 -> Color 255 255 0
    4 -> Color 255 128 0
    5 -> Color 255 0 0
    6 -> Color 255 0 255
    7 -> Color 128 0 255
    _ -> Color 255 255 255


drkColors : Int -> Float
drkColors i =
  case i of
    0 -> 1
    1 -> 0.6
    2 -> 0.8
    3 -> 0.4
    4 -> 0.9
    5 -> 0.7
    6 -> 0.5
    7 -> 0.3
    _ -> 0


ownerColor : Int -> Color
ownerColor i =
  if i < 0 then
    darkenColor (baseColors -1) (drkColors 3)
  else
    darkenColor
    (baseColors (modBy 8 i))
    (drkColors (i // 8))


darkenColor : Color -> Float -> Color
darkenColor base drk =
  { r = round (toFloat base.r * drk)
  , g = round (toFloat base.g * drk)
  , b = round (toFloat base.b * drk)
  }


colorString : Color -> String
colorString c =
  "rgb(" ++ String.fromInt c.r
  ++ " " ++ String.fromInt c.g
  ++ " " ++ String.fromInt c.b
  ++ ")"


-- MAIN


main =
  Browser.element
  { init = init
  , update = update
  , view = view
  , subscriptions = subscriptions
  }



-- MODEL


type alias Star =
  { x : Float
  , y : Float
  , owners : List (Int, Int)
  }


type Stars
  = Stars (List Star)
  | Loading
  | Failed String


type alias Model =
  { tick : Int
  , slider : SingleSlider Msg
  , stars : Stars
  , minX : Float
  , minY : Float
  , maxX : Float
  , maxY : Float
  , playing : Bool
  }


init : Json.Decode.Value -> ( Model, Cmd Msg )
init gameData =
  let
    initValue = 0
    stars = decodeGameData gameData
  in
  case stars of
    Stars starList ->
      ( { tick = minTick stars
        , stars = stars
        , minX = mapFold .x min 0 starList
        , minY = mapFold .y min 0 starList
        , maxX = mapFold .x max 0 starList
        , maxY = mapFold .y max 0 starList
        , playing = False
        , slider = SingleSlider.init
          { min = toFloat ( minTick stars )
          , max = toFloat ( maxTick stars )
          , value = initValue
          , step = 1
          , onChange = SliderChange
          } |> SingleSlider.withValueFormatter valueFormatter
        }
      , Cmd.none
      )
    _ -> ({ defaultModel | stars = stars }, Cmd.none)


defaultModel : Model
defaultModel =
  { tick = 0
  , stars = Loading
  , minX = 0
  , minY = 0
  , maxX = 0
  , maxY = 0
  , playing = False
  , slider = SingleSlider.init
    { min = 0
    , max = 0
    , value = 0
    , step = 1
    , onChange = SliderChange
    } |> SingleSlider.withValueFormatter valueFormatter
  }


-- SUBSCRIPTIONS


subscriptions : Model -> Sub Msg
subscriptions model =
  if model.playing then
    Time.every 41 Tick
  else 
    Sub.none


-- DECODING STARS


decodeGameData : Json.Decode.Value -> Stars
decodeGameData v =
  case Json.Decode.decodeValue gameDataDecoder v of
    Err error -> Failed ( getJsonErrorMessage error )
    Ok stars -> stars


gameDataDecoder : Decoder Stars
gameDataDecoder =
  Json.Decode.map Stars
  ( field "stars" 
    ( Json.Decode.map ( List.map ( \(_, x) -> x ) )
      ( Json.Decode.keyValuePairs starDecoder )
    )
  )


starDecoder : Decoder Star
starDecoder =
  Json.Decode.map3 Star
  ( field "x" float )
  ( field "y" float )
  ( field "owners"
    ( Json.Decode.map
      List.sort
      ( keyValuePairs int
      |> Json.Decode.andThen decodeKeyValues
      )
    )
  )


decodeKeyValues : List ( String, Int ) -> Decoder ( List ( Int, Int ) )
decodeKeyValues l =
  case List.foldr
    ( \x ->  Result.andThen ( decodeNextKeyValue x ) )
    ( Ok [] ) l
  of
    Ok keyValues -> Json.Decode.succeed keyValues
    Err message -> Json.Decode.fail message


decodeNextKeyValue : ( String, Int ) -> List ( Int, Int ) -> Result String ( List ( Int, Int ) )
decodeNextKeyValue ( keyString, value ) rest =
  case String.toInt keyString of
    Just key -> Ok ( ( key, value ) :: rest )
    Nothing -> Err ( keyString ++ "This is not a valid key number" )


getJsonErrorMessage : Json.Decode.Error -> String
getJsonErrorMessage error =
  case error of
    Json.Decode.Field field e -> field ++ " -> " ++ getJsonErrorMessage e
    Json.Decode.Index index e -> String.fromInt index ++ " -> " ++ getJsonErrorMessage e
    Json.Decode.OneOf l -> "Error in one of many parsers. This shouldn't happen." 
    Json.Decode.Failure message val -> message


-- UPDATE


type Msg
  = SliderChange Float
  | Tick Time.Posix
  | PauseTrigger


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
  case msg of
    SliderChange new_value ->
      ( { model
        | tick = round new_value
        , slider = SingleSlider.update new_value model.slider
        }
      , Cmd.none
      )
    Tick _ ->
      if model.tick < maxTick model.stars then
        ( { model
          | tick = model.tick + 1
          , slider = SingleSlider.update (toFloat model.tick + 1) model.slider
          }
        , Cmd.none
        )
      else
        ( { model | playing = False }
        , Cmd.none
        )
    PauseTrigger ->
      if model.tick < maxTick model.stars || model.playing then
        ( { model | playing = not model.playing }, Cmd.none )
      else
        ( { model
          | playing = True
          , tick = minTick model.stars
          }
        , Cmd.none
        )


-- SLIDER FORMATTERS

valueFormatter : Float -> Float -> String
valueFormatter val1 val2 =
  String.fromFloat val1 -- ++ " " ++ String.fromFloat val2


-- TIMELAPSE


timelapseView : Model -> Int -> Html Msg
timelapseView model tick =
  case model.stars of
    Loading -> text "Loading..."
    Failed message -> text ( "Error loading game: " ++ message )
    Stars stars ->
      svg
      [ viewBox
        ( String.fromFloat (model.minX - mapPadding)
        ++ " " ++ String.fromFloat (model.minY - mapPadding)
        ++ " " ++ String.fromFloat (model.maxX - model.minX + 2 * mapPadding)
        ++ " " ++ String.fromFloat (model.maxY - model.minY + 2 * mapPadding)
        )
      ]
      ( rect
        [ x ( String.fromFloat (model.minX - mapPadding) )
        , y ( String.fromFloat (model.minY - mapPadding) )
        , width ( String.fromFloat (model.maxX - model.minX + 2 * mapPadding) )
        , height ( String.fromFloat (model.maxY - model.minY + 2 * mapPadding) )
        ]
        []
      :: List.map ( starCircle tick ) stars )


starCircle : Int -> Star -> Svg Msg
starCircle tick star =
  circle
  [ cx ( String.fromFloat star.x )
  , cy ( String.fromFloat star.y )
  , r ( String.fromFloat starRadius )
  , fill ( getOwner tick star |> ownerColor |> colorString )
  ] []


getOwner : Int -> Star -> Int
getOwner tick star =
  case getOwnerHelper tick star.owners of
    Nothing -> -1
    Just owner -> owner


getOwnerHelper : Int -> List (Int, Int) -> Maybe Int
getOwnerHelper tick owners =
  case owners of
    [] -> Nothing
    ((change, owner) :: rest) ->
      if change > tick then Nothing
      else
        case getOwnerHelper tick rest of
          Nothing -> Just owner
          Just trueOwner -> Just trueOwner


mapFold : ( a -> b ) -> ( b -> c -> c ) -> c -> List a -> c
mapFold mapper folder id list =
  List.foldr folder id ( List.map mapper list )


minTick : Stars -> Int
minTick stars =
  case stars of
    Loading -> 0
    Failed _ -> 0
    Stars starList ->
      let id = maxTick stars
      in
        mapFold
        ( .owners >> mapFold first min id )
        min id starList


maxTick : Stars -> Int
maxTick stars =
  case stars of
    Loading -> 0
    Failed _ -> 0
    Stars starList ->
      mapFold
      ( .owners >> mapFold first max 0 )
      max 0 starList


-- VIEW


view : Model -> Html Msg
view model =
  div []
    [ timelapseView model model.tick
    , SingleSlider.view model.slider
    , br [] []
    , button
      [ onClick PauseTrigger
      , class "uk-button uk-button-primary uk-width-1-1"
      ]
      [ text ( if model.playing then "Pause" else "Play" ) ]
    ]
